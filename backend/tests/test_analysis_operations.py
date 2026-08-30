import math

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from app.analysis.errors import AnalysisInvalidColumnError, AnalysisValidationError
from app.analysis.executor import PandasAnalysisExecutor
from app.analysis.schemas import AnalysisPlan
from app.config import Settings


@pytest.fixture
def frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "region": ["East", "East", "West", "West", None],
            "sales": [10, 20, 5, 15, np.nan],
            "quantity": [1, 2, 1, 3, 2],
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-02-01", "2024-02-02", "2024-02-03"]),
            "note": ["alpha", "alphabet", "beta", None, "gamma"],
        }
    )


def run(frame, *operations, **settings):
    config = Settings(database_url="sqlite://", **settings)
    plan = AnalysisPlan.model_validate({"operations": list(operations)})
    return PandasAnalysisExecutor(config).execute(frame, plan)


def test_summarize(frame):
    result = run(frame, {"type": "summarize", "columns": ["sales", "region"]})
    assert result.row_count == 2
    assert "missing_count" in result.columns


@pytest.mark.parametrize(
    "aggregation,expected", [("sum", 50.0), ("mean", 12.5), ("median", 12.5), ("min", 5.0), ("max", 20.0), ("count", 4), ("nunique", 4)]
)
def test_groupby_aggregations(frame, aggregation, expected):
    result = run(frame, {"type": "groupby_aggregate", "group_by": [], "metrics": [{"column": "sales", "aggregation": aggregation}]})
    assert result.rows[0][0] == expected


def test_groupby_multi_metric_sort_limit(frame):
    result = run(
        frame,
        {
            "type": "groupby_aggregate",
            "group_by": ["region"],
            "metrics": [{"column": "sales", "aggregation": "sum"}, {"column": "quantity", "aggregation": "mean"}],
            "sort": [{"column": "sales_sum", "direction": "desc"}],
            "limit": 2,
        },
    )
    assert result.rows[0][0] == "East"
    assert len(result.columns) == 3


@pytest.mark.parametrize(
    "condition,count",
    [
        ({"column": "sales", "operator": "gt", "value": 10}, 2),
        ({"column": "region", "operator": "eq", "value": "East"}, 2),
        ({"column": "region", "operator": "is_null"}, 1),
        ({"column": "sales", "operator": "not_null"}, 4),
        ({"column": "note", "operator": "contains", "value": "alpha"}, 2),
        ({"column": "note", "operator": "starts_with", "value": "b"}, 1),
        ({"column": "region", "operator": "in", "value": ["East"]}, 2),
        ({"column": "region", "operator": "not_in", "value": ["East"]}, 3),
    ],
)
def test_filters(frame, condition, count):
    assert run(frame, {"type": "filter_rows", "conditions": [condition]}).row_count == count


def test_sort_and_top_n(frame):
    result = run(
        frame,
        {"type": "sort_rows", "sort": [{"column": "quantity", "direction": "desc"}]},
        {"type": "top_n", "column": "sales", "n": 2, "direction": "desc"},
    )
    assert result.rows[0][1] == 20.0


def test_correlation(frame):
    result = run(frame, {"type": "correlation", "columns": ["sales", "quantity"], "method": "pearson"})
    assert result.columns == ["column_a", "column_b", "correlation"]


def test_value_counts(frame):
    result = run(frame, {"type": "value_counts", "column": "region", "top_n": 2, "dropna": True})
    assert result.rows[0][0] == "East"
    assert result.rows[0][1] == 2


def test_descriptive_statistics(frame):
    result = run(frame, {"type": "descriptive_statistics", "columns": ["sales"]})
    assert "mean" in result.columns
    assert result.rows[0][0] == "sales"


@pytest.mark.parametrize("frequency,expected", [("day", 5), ("month", 2)])
def test_time_series(frame, frequency, expected):
    result = run(
        frame,
        {
            "type": "time_series_aggregate",
            "datetime_column": "date",
            "frequency": frequency,
            "metric": {"column": "sales", "aggregation": "sum"},
        },
    )
    assert result.row_count == expected


@pytest.mark.parametrize("operation,expected", [("add", 12.0), ("multiply", 10.0)])
def test_derived_columns(frame, operation, expected):
    result = run(
        frame,
        {
            "type": "derive_column",
            "name": "derived",
            "operation": operation,
            "left": {"type": "column", "value": "sales"},
            "right": {"type": "column" if operation == "multiply" else "constant", "value": "quantity" if operation == "multiply" else 2},
        },
    )
    assert result.rows[0][-1] == expected


def test_divide_zero_is_null(frame):
    result = run(
        frame,
        {
            "type": "derive_column",
            "name": "ratio",
            "operation": "divide",
            "left": {"type": "column", "value": "sales"},
            "right": {"type": "constant", "value": 0},
        },
    )
    assert result.rows[0][-1] is None


def test_pipeline_chaining(frame):
    result = run(
        frame,
        {"type": "filter_rows", "conditions": [{"column": "sales", "operator": "gte", "value": 10}]},
        {
            "type": "derive_column",
            "name": "revenue",
            "operation": "multiply",
            "left": {"type": "column", "value": "sales"},
            "right": {"type": "column", "value": "quantity"},
        },
        {"type": "groupby_aggregate", "group_by": ["region"], "metrics": [{"column": "revenue", "aggregation": "sum"}]},
        {"type": "sort_rows", "sort": [{"column": "revenue_sum", "direction": "desc"}]},
    )
    assert result.row_count == 2
    assert len(result.operations_executed) == 4


@pytest.mark.parametrize(
    "untrusted", ["__import__('os').system('calc')", "../../secret.csv", "https://evil.test/data", "lambda x: x", "open('secret')"]
)
def test_invalid_column_and_injection_are_never_executed(frame, untrusted):
    with pytest.raises(AnalysisInvalidColumnError):
        run(frame, {"type": "summarize", "columns": [untrusted]})


def test_invalid_operation_and_aggregation_schema():
    with pytest.raises(ValidationError):
        AnalysisPlan.model_validate({"operations": [{"type": "python", "code": "import os"}]})
    with pytest.raises(ValidationError):
        AnalysisPlan.model_validate(
            {"operations": [{"type": "groupby_aggregate", "group_by": ["a"], "metrics": [{"column": "b", "aggregation": "apply"}]}]}
        )


def test_operation_and_result_limits(frame):
    operation = {"type": "sort_rows", "sort": [{"column": "sales", "direction": "asc"}]}
    with pytest.raises(AnalysisValidationError):
        run(frame, *([operation] * 3), analysis_max_operations=2)
    result = run(frame, operation, analysis_max_result_rows=2, analysis_max_result_cells=100)
    assert result.row_count == 2
    assert result.truncated


def test_result_cell_limit(frame):
    result = run(
        frame,
        {"type": "sort_rows", "sort": [{"column": "sales", "direction": "asc"}]},
        analysis_max_result_rows=100,
        analysis_max_result_cells=5,
    )
    assert result.row_count == 1
    assert result.truncated
