import time
from typing import Any

import numpy as np
import pandas as pd

from app.analysis.errors import AnalysisInvalidColumnError, AnalysisResultTooLargeError, AnalysisValidationError
from app.analysis.schemas import AnalysisPlan, AnalysisResult, FilterCondition, OperationTrace
from app.config import Settings
from app.query.executor import json_value


class PandasAnalysisExecutor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def execute(self, source: pd.DataFrame, plan: AnalysisPlan, sampled: bool = False) -> AnalysisResult:
        if len(plan.operations) > self.settings.analysis_max_operations:
            raise AnalysisValidationError("Analysis operation limit exceeded.")
        if len(source.columns) > self.settings.analysis_max_columns:
            raise AnalysisValidationError("Dataset column limit exceeded.")
        frame = source
        traces = []
        started = time.perf_counter()
        input_rows = len(frame)
        for index, operation in enumerate(plan.operations, 1):
            before = len(frame)
            step_started = time.perf_counter()
            frame = self._operation(frame, operation)
            traces.append(
                OperationTrace(
                    step=index,
                    type=operation.type,
                    duration_ms=round((time.perf_counter() - step_started) * 1000, 3),
                    input_rows=before,
                    output_rows=len(frame),
                )
            )
        max_by_cells = max(1, self.settings.analysis_max_result_cells // max(1, len(frame.columns)))
        limit = min(self.settings.analysis_max_result_rows, max_by_cells)
        truncated = len(frame) > limit
        output = frame.head(limit)
        rows = [[json_value(value) for value in row] for row in output.itertuples(index=False, name=None)]
        return AnalysisResult(
            columns=[str(c) for c in output.columns],
            rows=rows,
            row_count=len(rows),
            truncated=truncated,
            execution_time_ms=round((time.perf_counter() - started) * 1000, 3),
            operations_executed=traces,
            warnings=["Analysis used a deterministic sample; metrics are not full-dataset totals."] if sampled else [],
            metadata={"sampled": sampled, "source_rows": input_rows, "analyzed_rows": input_rows},
        )

    def _columns(self, frame: pd.DataFrame, columns: list[str]) -> None:
        missing = [column for column in columns if column not in frame.columns]
        if missing:
            raise AnalysisInvalidColumnError(f"Unknown column: {missing[0]}")

    def _operation(self, frame: pd.DataFrame, operation):
        kind = operation.type
        if kind == "filter_rows":
            mask = pd.Series(True, index=frame.index)
            for condition in operation.conditions:
                self._columns(frame, [condition.column])
                mask &= self._filter(frame[condition.column], condition)
            return frame.loc[mask]
        if kind == "derive_column":
            if operation.name in frame.columns:
                raise AnalysisValidationError("Derived column name already exists.")
            left = self._operand(frame, operation.left)
            right = self._operand(frame, operation.right)
            if operation.operation == "add":
                result = left + right
            elif operation.operation == "subtract":
                result = left - right
            elif operation.operation == "multiply":
                result = left * right
            else:
                denominator = right.replace(0, np.nan) if isinstance(right, pd.Series) else (np.nan if right == 0 else right)
                result = left / denominator
            output = frame.copy()
            output[operation.name] = result
            return output
        if kind == "groupby_aggregate":
            if (
                len(operation.group_by) > self.settings.analysis_max_groupby_columns
                or len(operation.metrics) > self.settings.analysis_max_metrics
            ):
                raise AnalysisValidationError("GroupBy limit exceeded.")
            columns = operation.group_by + [m.column for m in operation.metrics]
            self._columns(frame, columns)
            named = {f"{m.column}_{m.aggregation}": pd.NamedAgg(column=m.column, aggfunc=m.aggregation) for m in operation.metrics}
            if operation.group_by:
                output = frame.groupby(operation.group_by, dropna=False).agg(**named).reset_index()
            else:
                output = pd.DataFrame(
                    [{alias: getattr(frame[metric.column], metric.aggregation)() for alias, metric in zip(named, operation.metrics)}]
                )
            if operation.sort:
                output = self._sort(output, operation.sort)
            return output.head(operation.limit) if operation.limit else output
        if kind == "sort_rows":
            return self._sort(frame, operation.sort)
        if kind == "top_n":
            self._columns(frame, [operation.column])
            return frame.sort_values(operation.column, ascending=operation.direction == "asc").head(operation.n)
        if kind == "value_counts":
            self._columns(frame, [operation.column])
            counts = (
                frame[operation.column]
                .value_counts(dropna=operation.dropna)
                .head(min(operation.top_n, self.settings.analysis_max_top_values))
            )
            total = len(frame)
            return pd.DataFrame(
                {"value": counts.index.astype(object), "count": counts.values, "ratio": counts.values / total if total else 0}
            )
        if kind == "correlation":
            self._columns(frame, operation.columns)
            if len(operation.columns) > self.settings.analysis_max_columns:
                raise AnalysisValidationError("Correlation column limit exceeded.")
            numeric = frame[operation.columns].apply(pd.to_numeric, errors="coerce")
            matrix = numeric.corr(method=operation.method)
            return pd.DataFrame(
                [
                    {"column_a": a, "column_b": b, "correlation": matrix.loc[a, b]}
                    for i, a in enumerate(operation.columns)
                    for b in operation.columns[i + 1 :]
                    if pd.notna(matrix.loc[a, b])
                ]
            )
        if kind == "descriptive_statistics":
            columns = operation.columns or list(frame.select_dtypes(include="number").columns)
            self._columns(frame, columns)
            if len(columns) > self.settings.analysis_max_columns:
                raise AnalysisValidationError("Analysis column limit exceeded.")
            return (
                frame[columns]
                .describe(percentiles=[0.25, 0.5, 0.75])
                .rename(index={"25%": "q1", "50%": "median", "75%": "q3"})
                .T.reset_index(names="column")
            )
        if kind == "summarize":
            columns = operation.columns or list(frame.columns)
            self._columns(frame, columns)
            records = []
            for name in columns:
                series = frame[name]
                base = {
                    "column": name,
                    "count": int(series.count()),
                    "missing_count": int(series.isna().sum()),
                    "unique_count": int(series.nunique(dropna=True)),
                }
                if pd.api.types.is_numeric_dtype(series):
                    base.update(
                        {
                            key: json_value(value)
                            for key, value in {
                                "min": series.min(),
                                "max": series.max(),
                                "mean": series.mean(),
                                "median": series.median(),
                                "std": series.std(),
                                "sum": series.sum(),
                            }.items()
                        }
                    )
                else:
                    base["top_values"] = str(series.value_counts().head(5).to_dict())
                records.append(base)
            return pd.DataFrame(records)
        if kind == "time_series_aggregate":
            columns = [operation.datetime_column, operation.metric.column, *operation.group_by]
            self._columns(frame, columns)
            if len(operation.group_by) > self.settings.analysis_max_groupby_columns:
                raise AnalysisValidationError("Time series group limit exceeded.")
            frequency = {"day": "D", "week": "W", "month": "M", "quarter": "Q", "year": "Y"}[operation.frequency]
            output = frame.copy()
            output[operation.datetime_column] = pd.to_datetime(output[operation.datetime_column], errors="coerce")
            output = output.dropna(subset=[operation.datetime_column])
            output[operation.datetime_column] = output[operation.datetime_column].dt.to_period(frequency).dt.start_time
            groups = [operation.datetime_column, *operation.group_by]
            return (
                output.groupby(groups, dropna=False)[operation.metric.column]
                .agg(operation.metric.aggregation)
                .reset_index(name=f"{operation.metric.column}_{operation.metric.aggregation}")
            )
        raise AnalysisValidationError("Unsupported analysis operation.")

    def _sort(self, frame, specs):
        if len(specs) > self.settings.analysis_max_sort_columns:
            raise AnalysisValidationError("Sort column limit exceeded.")
        columns = [item.column for item in specs]
        self._columns(frame, columns)
        return frame.sort_values(columns, ascending=[item.direction == "asc" for item in specs])

    def _operand(self, frame, operand):
        if operand.type == "constant":
            if not isinstance(operand.value, (int, float)):
                raise AnalysisValidationError("Derived constants must be numeric.")
            return operand.value
        column = str(operand.value)
        self._columns(frame, [column])
        return pd.to_numeric(frame[column], errors="coerce")

    @staticmethod
    def _filter(series: pd.Series, condition: FilterCondition) -> pd.Series:
        operator, value = condition.operator, condition.value
        if operator == "is_null":
            return series.isna()
        if operator == "not_null":
            return series.notna()
        if operator in ("in", "not_in"):
            if not isinstance(value, list):
                raise AnalysisValidationError("IN filter value must be a list.")
            result = series.isin(value)
            return ~result if operator == "not_in" else result
        if operator in ("contains", "starts_with", "ends_with"):
            strings = series.astype("string")
            method = {
                "contains": lambda: strings.str.contains(str(value), regex=False, na=False),
                "starts_with": lambda: strings.str.startswith(str(value), na=False),
                "ends_with": lambda: strings.str.endswith(str(value), na=False),
            }
            return method[operator]()
        return {
            "eq": lambda: series.eq(value),
            "ne": lambda: series.ne(value),
            "gt": lambda: series.gt(value),
            "gte": lambda: series.ge(value),
            "lt": lambda: series.lt(value),
            "lte": lambda: series.le(value),
        }[operator]().fillna(False)
