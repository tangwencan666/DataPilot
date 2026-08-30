import numpy as np
import pandas as pd
import pytest

from app.config import Settings
from app.profiling.service import ProfilingService
from app.profiling.types import SemanticType


def profiler(**overrides) -> ProfilingService:
    return ProfilingService(Settings(database_url="sqlite://", **overrides))


def column(result, name: str):
    return next(item for item in result.columns if item.name == name)


def test_numeric_statistics_missing_duplicates_and_outlier() -> None:
    frame = pd.DataFrame({"value": [1, 2, 2, 3, 4, 100, np.nan], "group": ["a", "a", "a", "b", "b", "c", None]})
    result = profiler().profile(frame)
    numeric = column(result, "value").numeric
    assert numeric is not None
    assert numeric.min == 1
    assert numeric.max == 100
    assert numeric.median == 2.5
    assert numeric.outlier_count == 1
    assert result.summary.missing_cell_count == 2
    assert any(issue.code == "NUMERIC_OUTLIERS" for issue in result.issues)


def test_duplicate_rows() -> None:
    result = profiler().profile(pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]}))
    assert result.summary.duplicate_row_count == 1
    assert result.summary.duplicate_row_ratio == pytest.approx(1 / 3, abs=1e-6)


def test_categorical_top_values_and_high_cardinality() -> None:
    values = [f"C{i}" for i in range(90)] + [f"C{i}" for i in range(10)]
    result = profiler(profile_high_cardinality_min=50, profile_high_cardinality_ratio=0.8).profile(pd.DataFrame({"category": values}))
    categorical = column(result, "category").categorical
    assert categorical is not None
    assert categorical.top_values[0].count == 2
    assert categorical.is_high_cardinality
    assert any(issue.code == "HIGH_CARDINALITY" for issue in result.issues)


def test_constant_and_all_missing_columns() -> None:
    result = profiler().profile(pd.DataFrame({"constant": [5, 5, 5], "empty": [None, None, None]}))
    assert column(result, "constant").is_constant
    assert column(result, "empty").is_all_missing
    assert {issue.code for issue in result.issues} >= {"CONSTANT_COLUMN", "ALL_MISSING_COLUMN"}


def test_correlation_is_filtered_and_sorted() -> None:
    result = profiler(profile_correlation_threshold=0.5).profile(
        pd.DataFrame({"a": range(20), "b": [v * 2 for v in range(20)], "c": [1, 0] * 10})
    )
    assert result.correlations[0].column_a == "a"
    assert result.correlations[0].column_b == "b"
    assert result.correlations[0].correlation == 1.0


def test_datetime_boolean_and_text_profiles() -> None:
    frame = pd.DataFrame(
        {
            "when": pd.to_datetime(["2024-01-01", "2024-01-03", None]),
            "enabled": pd.Series([True, False, None], dtype="boolean"),
            "notes": ["a long free-form sentence " * 3, "", "another long free-form sentence " * 3],
        }
    )
    result = profiler().profile(frame)
    assert column(result, "when").datetime.range_days == 2
    assert column(result, "enabled").boolean.true_count == 1
    assert column(result, "notes").semantic_type == SemanticType.TEXT
    assert column(result, "notes").text.empty_string_count == 1
    assert any(issue.code == "EMPTY_STRINGS" for issue in result.issues)


def test_infinite_values_and_zero_iqr() -> None:
    result = profiler().profile(pd.DataFrame({"value": [1.0, 1.0, 1.0, np.inf, -np.inf]}))
    numeric = column(result, "value").numeric
    assert numeric.infinite_count == 2
    assert numeric.outlier_count == 0
    assert any(issue.code == "INFINITE_VALUES" for issue in result.issues)


def test_quality_score_is_deterministic_and_bounded() -> None:
    good = profiler().profile(pd.DataFrame({"a": range(100), "b": range(100)})).summary.quality_score
    bad = profiler().profile(pd.DataFrame({"a": [None] * 100, "b": [1] * 100})).summary.quality_score
    assert 0 <= bad <= good <= 100
    assert good == profiler().profile(pd.DataFrame({"a": range(100), "b": range(100)})).summary.quality_score


def test_sampling_metadata() -> None:
    result = profiler(profile_max_rows=5, profile_sample_rows=3).profile(pd.DataFrame({"a": range(10)}))
    assert result.sampling.is_sampled
    assert result.sampling.sampled_row_count == 3
    assert result.sampling.source_row_count == 10
    assert result.sampling.statistics_scope == "sample"
