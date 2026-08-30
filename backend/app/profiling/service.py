import math
from typing import Any

import numpy as np
import pandas as pd
from pandas.api import types as ptypes

from app.config import Settings
from app.profiling.types import (
    BooleanProfile, CategoricalProfile, ColumnProfile, CorrelationPair, DataQualityIssue,
    DatasetProfileSummary, DatetimeProfile, IssueSeverity, NumericProfile, ProfileResult,
    SamplingInfo, SemanticType, TextProfile, TopValue,
)


def _ratio(value: int | float, total: int) -> float:
    return round(float(value) / total, 6) if total else 0.0


def _finite(value: Any) -> float | None:
    if value is None or not math.isfinite(float(value)):
        return None
    return round(float(value), 6)


def _json_value(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return pd.Timestamp(value).isoformat()
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


class ProfilingService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def profile(self, source: pd.DataFrame) -> ProfileResult:
        source_rows = len(source)
        is_sampled = source_rows > self.settings.profile_max_rows
        frame = source.sample(n=min(self.settings.profile_sample_rows, source_rows), random_state=42) if is_sampled else source
        rows, columns_count = frame.shape
        duplicate_count = int(frame.duplicated().sum())
        missing_count = int(frame.isna().sum().sum())
        column_profiles: list[ColumnProfile] = []
        issues: list[DataQualityIssue] = []

        for name in frame.columns:
            column_profiles.append(self._profile_column(str(name), frame[name], rows, issues))

        counts = {kind: sum(item.semantic_type == kind for item in column_profiles) for kind in SemanticType}
        constant_count = sum(item.is_constant for item in column_profiles)
        all_missing_count = sum(item.is_all_missing for item in column_profiles)
        high_cardinality_count = sum(bool(item.categorical and item.categorical.is_high_cardinality) for item in column_profiles)
        duplicate_ratio = _ratio(duplicate_count, rows)
        missing_ratio = _ratio(missing_count, rows * columns_count)
        if duplicate_ratio >= self.settings.quality_high_duplicate_threshold:
            issues.append(DataQualityIssue(code="HIGH_DUPLICATE_RATIO", severity=IssueSeverity.WARNING, title="重复行比例较高", description="分析范围内存在较多完全重复的数据行。", metric="duplicate_row_ratio", value=duplicate_ratio))

        score = self._quality_score(missing_ratio, duplicate_ratio, all_missing_count, constant_count, issues)
        summary = DatasetProfileSummary(
            row_count=source_rows, column_count=columns_count, total_cells=source_rows * columns_count,
            missing_cell_count=missing_count, missing_cell_ratio=missing_ratio,
            duplicate_row_count=duplicate_count, duplicate_row_ratio=duplicate_ratio,
            numeric_column_count=counts[SemanticType.NUMERIC], categorical_column_count=counts[SemanticType.CATEGORICAL],
            text_column_count=counts[SemanticType.TEXT], datetime_column_count=counts[SemanticType.DATETIME],
            boolean_column_count=counts[SemanticType.BOOLEAN], constant_column_count=constant_count,
            all_missing_column_count=all_missing_count, high_cardinality_column_count=high_cardinality_count, quality_score=score,
        )
        return ProfileResult(summary=summary,
            sampling=SamplingInfo(is_sampled=is_sampled, sampled_row_count=rows, source_row_count=source_rows, statistics_scope="sample" if is_sampled else "full_dataset"),
            columns=column_profiles, correlations=self._correlations(frame, column_profiles), issues=issues)

    def _semantic_type(self, series: pd.Series, unique_count: int, rows: int) -> SemanticType:
        if ptypes.is_bool_dtype(series.dtype): return SemanticType.BOOLEAN
        if ptypes.is_datetime64_any_dtype(series.dtype): return SemanticType.DATETIME
        if ptypes.is_numeric_dtype(series.dtype): return SemanticType.NUMERIC
        non_null = series.dropna()
        if non_null.empty: return SemanticType.UNKNOWN
        strings = non_null.astype(str)
        date_hint = strings.str.contains(r"[-/:T]", regex=True).mean() >= 0.8
        if date_hint:
            parsed = pd.to_datetime(strings, errors="coerce")
            if parsed.notna().mean() >= 0.8: return SemanticType.DATETIME
        unique_ratio = _ratio(unique_count, len(non_null))
        average_length = strings.str.len().mean()
        return SemanticType.CATEGORICAL if unique_count <= 100 and average_length <= 32 else SemanticType.TEXT

    def _profile_column(self, name: str, series: pd.Series, rows: int, issues: list[DataQualityIssue]) -> ColumnProfile:
        non_null = series.dropna(); non_null_count = len(non_null); missing_count = rows - non_null_count
        unique_count = int(non_null.nunique()); unique_ratio = _ratio(unique_count, non_null_count)
        semantic = self._semantic_type(series, unique_count, rows)
        is_all_missing = non_null_count == 0; is_constant = non_null_count > 0 and unique_count == 1
        common = dict(name=name, physical_dtype=str(series.dtype), semantic_type=semantic, count=rows,
            non_null_count=non_null_count, missing_count=missing_count, missing_ratio=_ratio(missing_count, rows),
            unique_count=unique_count, unique_ratio=unique_ratio, is_constant=is_constant, is_all_missing=is_all_missing,
            sample_values=[_json_value(v) for v in non_null.drop_duplicates().head(self.settings.profile_sample_values).tolist()])
        self._common_issues(name, common, issues)
        if semantic == SemanticType.NUMERIC: return ColumnProfile(**common, numeric=self._numeric(non_null, rows, name, issues))
        if semantic == SemanticType.BOOLEAN: return ColumnProfile(**common, boolean=self._boolean(non_null, rows))
        if semantic == SemanticType.DATETIME: return ColumnProfile(**common, datetime=self._datetime(non_null))
        if semantic == SemanticType.CATEGORICAL:
            high = unique_count >= self.settings.profile_high_cardinality_min and unique_ratio >= self.settings.profile_high_cardinality_ratio
            if high: issues.append(DataQualityIssue(code="HIGH_CARDINALITY", severity=IssueSeverity.WARNING, title="类别基数较高", description="类别列包含大量不同值。", column=name, metric="unique_ratio", value=unique_ratio))
            return ColumnProfile(**common, categorical=CategoricalProfile(unique_count=unique_count, top_values=self._top_values(non_null, rows), is_high_cardinality=high))
        if semantic == SemanticType.TEXT: return ColumnProfile(**common, text=self._text(non_null, rows, name, issues))
        return ColumnProfile(**common)

    def _common_issues(self, name: str, data: dict[str, Any], issues: list[DataQualityIssue]) -> None:
        if data["is_all_missing"]: issues.append(DataQualityIssue(code="ALL_MISSING_COLUMN", severity=IssueSeverity.ERROR, title="字段全部缺失", description="该字段没有任何有效值。", column=name, metric="missing_ratio", value=1.0))
        elif data["is_constant"]: issues.append(DataQualityIssue(code="CONSTANT_COLUMN", severity=IssueSeverity.INFO, title="常量字段", description="该字段所有非空值都相同。", column=name, metric="unique_count", value=1))
        if data["missing_ratio"] >= self.settings.quality_high_missing_threshold and not data["is_all_missing"]: issues.append(DataQualityIssue(code="HIGH_MISSING_RATIO", severity=IssueSeverity.WARNING, title="缺失比例较高", description="该字段的缺失值比例超过配置阈值。", column=name, metric="missing_ratio", value=data["missing_ratio"]))
        if data["unique_ratio"] >= 0.98 and data["unique_count"] >= 20: issues.append(DataQualityIssue(code="VERY_HIGH_UNIQUE_RATIO", severity=IssueSeverity.INFO, title="唯一值比例很高", description="该字段几乎每行都是不同值。", column=name, metric="unique_ratio", value=data["unique_ratio"]))

    def _numeric(self, values: pd.Series, rows: int, name: str, issues: list[DataQualityIssue]) -> NumericProfile:
        numeric = pd.to_numeric(values, errors="coerce"); infinite_count = int(np.isinf(numeric).sum()); finite = numeric[np.isfinite(numeric)]
        q1 = finite.quantile(.25) if len(finite) else None; q3 = finite.quantile(.75) if len(finite) else None
        iqr = float(q3 - q1) if q1 is not None and q3 is not None else None
        outlier_count = 0 if not iqr or iqr == 0 else int(((finite < q1 - 1.5 * iqr) | (finite > q3 + 1.5 * iqr)).sum())
        if outlier_count: issues.append(DataQualityIssue(code="NUMERIC_OUTLIERS", severity=IssueSeverity.WARNING, title="检测到数值异常值", description="使用 IQR 方法检测到超出 1.5×IQR 范围的值。", column=name, metric="outlier_ratio", value=_ratio(outlier_count, len(finite))))
        if infinite_count: issues.append(DataQualityIssue(code="INFINITE_VALUES", severity=IssueSeverity.ERROR, title="包含无限值", description="字段包含正或负无穷值。", column=name, metric="infinite_count", value=infinite_count))
        quantile = lambda q: _finite(finite.quantile(q)) if len(finite) else None
        return NumericProfile(min=_finite(finite.min()) if len(finite) else None, max=_finite(finite.max()) if len(finite) else None,
            mean=_finite(finite.mean()) if len(finite) else None, median=_finite(finite.median()) if len(finite) else None,
            std=_finite(finite.std()) if len(finite) > 1 else None, variance=_finite(finite.var()) if len(finite) > 1 else None,
            q1=_finite(q1), q3=_finite(q3), iqr=_finite(iqr), p01=quantile(.01), p05=quantile(.05), p95=quantile(.95), p99=quantile(.99),
            zero_count=int((finite == 0).sum()), zero_ratio=_ratio(int((finite == 0).sum()), rows), negative_count=int((finite < 0).sum()),
            negative_ratio=_ratio(int((finite < 0).sum()), rows), outlier_count=outlier_count, outlier_ratio=_ratio(outlier_count, len(finite)), infinite_count=infinite_count)

    def _top_values(self, values: pd.Series, rows: int) -> list[TopValue]:
        return [TopValue(value=_json_value(value), count=int(count), ratio=_ratio(int(count), rows)) for value, count in values.value_counts().head(self.settings.profile_top_values).items()]

    def _text(self, values: pd.Series, rows: int, name: str, issues: list[DataQualityIssue]) -> TextProfile:
        strings = values.astype(str); lengths = strings.str.len(); empty_count = int(strings.str.strip().eq("").sum())
        if empty_count: issues.append(DataQualityIssue(code="EMPTY_STRINGS", severity=IssueSeverity.WARNING, title="包含空字符串", description="字段包含去除空白后为空的字符串。", column=name, metric="empty_string_count", value=empty_count))
        return TextProfile(average_length=_finite(lengths.mean()) if len(lengths) else None, min_length=int(lengths.min()) if len(lengths) else None,
            max_length=int(lengths.max()) if len(lengths) else None, empty_string_count=empty_count, top_values=self._top_values(strings, rows))

    def _datetime(self, values: pd.Series) -> DatetimeProfile:
        parsed = pd.to_datetime(values, errors="coerce").dropna(); minimum = parsed.min() if len(parsed) else None; maximum = parsed.max() if len(parsed) else None
        distribution = lambda series: {str(k): int(v) for k, v in series.value_counts().sort_index().items()}
        return DatetimeProfile(min_datetime=minimum, max_datetime=maximum, range_days=_finite((maximum - minimum).total_seconds() / 86400) if minimum is not None else None,
            year_distribution=distribution(parsed.dt.year), month_distribution=distribution(parsed.dt.month), weekday_distribution=distribution(parsed.dt.day_name()))

    def _boolean(self, values: pd.Series, rows: int) -> BooleanProfile:
        true_count = int((values == True).sum()); false_count = int((values == False).sum())  # noqa: E712
        return BooleanProfile(true_count=true_count, false_count=false_count, true_ratio=_ratio(true_count, rows), false_ratio=_ratio(false_count, rows))

    def _correlations(self, frame: pd.DataFrame, profiles: list[ColumnProfile]) -> list[CorrelationPair]:
        names = [p.name for p in profiles if p.semantic_type == SemanticType.NUMERIC and not p.is_constant][:self.settings.profile_max_correlation_columns]
        if len(names) < 2: return []
        matrix = frame[names].replace([np.inf, -np.inf], np.nan).corr(method="pearson")
        pairs = [CorrelationPair(column_a=a, column_b=b, correlation=round(float(matrix.loc[a, b]), 6)) for i, a in enumerate(names) for b in names[i + 1:] if pd.notna(matrix.loc[a, b]) and abs(matrix.loc[a, b]) >= self.settings.profile_correlation_threshold]
        return sorted(pairs, key=lambda item: abs(item.correlation), reverse=True)[:self.settings.profile_max_correlations]

    @staticmethod
    def _quality_score(missing: float, duplicates: float, all_missing: int, constants: int, issues: list[DataQualityIssue]) -> float:
        severity_penalty = min(20, sum(5 if issue.severity == IssueSeverity.ERROR else 2 if issue.severity == IssueSeverity.WARNING else 0 for issue in issues))
        penalty = missing * 30 + duplicates * 20 + min(30, all_missing * 10) + min(10, constants * 2) + severity_penalty
        return round(max(0.0, min(100.0, 100.0 - penalty)), 2)
