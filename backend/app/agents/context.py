import json
from dataclasses import dataclass
from app.config import Settings
from app.models import Dataset, DatasetProfile


@dataclass
class AgentContext:
    payload: dict
    metadata: dict


class AgentContextBuilder:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def build(self, dataset: Dataset, profile: DatasetProfile | None) -> AgentContext:
        data = {
            "dataset": {"name": dataset.name, "row_count": dataset.row_count, "column_count": dataset.column_count},
            "tools": {
                "SQL": "Natural-language read-only query via validated SQL",
                "ANALYSIS": "Controlled AnalysisPlan operations only",
                "CHART": "Validated ChartSpec and safe ECharts builder",
            },
            "restrictions": ["No files, paths, network, shell, Python code, raw SQL, or raw JavaScript"],
        }
        truncated = False
        if profile and profile.profile_json:
            raw = profile.profile_json
            columns = []
            for col in raw.get("columns", [])[: self.settings.agent_max_context_columns]:
                item = {k: col.get(k) for k in ("name", "physical_dtype", "semantic_type", "missing_ratio", "unique_count")}
                item["sample_values"] = col.get("sample_values", [])[: self.settings.agent_max_sample_values]
                for kind in ("numeric", "categorical", "datetime"):
                    if col.get(kind):
                        item[kind] = {
                            k: v
                            for k, v in col[kind].items()
                            if k in {"min", "max", "mean", "median", "top_values", "min_datetime", "max_datetime", "range_days"}
                        }
                columns.append(item)
            data["profile"] = {
                "quality_score": profile.quality_score,
                "columns": columns,
                "issues": raw.get("issues", [])[: self.settings.agent_max_quality_issues],
                "correlations": raw.get("correlations", [])[: self.settings.agent_max_correlations],
            }
            truncated = (
                len(raw.get("columns", [])) > len(columns)
                or len(raw.get("issues", [])) > self.settings.agent_max_quality_issues
                or len(raw.get("correlations", [])) > self.settings.agent_max_correlations
            )
        encoded = json.dumps(data, ensure_ascii=False, default=str)
        if len(encoded) > self.settings.agent_max_context_chars:
            truncated = True
            data["profile"] = {
                "quality_score": profile.quality_score if profile else None,
                "columns": data.get("profile", {}).get("columns", [])[:10],
                "note": "Context deterministically reduced to fit budget.",
            }
            encoded = json.dumps(data, ensure_ascii=False, default=str)
            if len(encoded) > self.settings.agent_max_context_chars:
                data = {"dataset": data["dataset"], "tools": data["tools"], "restrictions": data["restrictions"]}
        return AgentContext(
            data,
            {
                "context_truncated": truncated,
                "context_chars": len(json.dumps(data, ensure_ascii=False, default=str)),
                "included_columns": len(data.get("profile", {}).get("columns", [])),
            },
        )
