import json
from app.agents.errors import AgentInvalidPlanError
from app.agents.schemas import AgentPlan
from app.charts.schemas import BarSpec, BoxplotSpec, HistogramSpec, LineSpec, PieSpec, ScatterSpec
from app.config import Settings

FORBIDDEN = (
    "python_code",
    "shell",
    "browser",
    "http://",
    "https://",
    "file://",
    "eval(",
    "exec(",
    "new function",
    "..\\",
    "../",
    "c:\\",
    "/etc/",
)


class AgentPlanValidator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def validate(self, plan: AgentPlan, columns: dict[str, str] | None = None) -> list[str]:
        if len(plan.steps) > self.settings.agent_max_steps:
            raise AgentInvalidPlanError("Plan exceeds AGENT_MAX_STEPS.")
        ids = [s.id for s in plan.steps]
        if len(ids) != len(set(ids)):
            raise AgentInvalidPlanError("Step ids must be unique.")
        seen: set[str] = set()
        for step in plan.steps:
            if step.id in step.depends_on:
                raise AgentInvalidPlanError("A step cannot depend on itself.")
            for dep in step.depends_on:
                if dep not in ids:
                    raise AgentInvalidPlanError(f"Unknown dependency '{dep}'.")
                if dep not in seen:
                    raise AgentInvalidPlanError("Dependencies must reference earlier steps.")
            serialized = json.dumps(step.input.model_dump(mode="json"), ensure_ascii=False).lower()
            if any(token in serialized for token in FORBIDDEN):
                raise AgentInvalidPlanError("Plan contains forbidden code, network, or filesystem input.")
            if columns:
                self._validate_columns(step, columns)
            seen.add(step.id)
        return ids

    def _validate_columns(self, step, columns: dict[str, str]) -> None:
        def require(name: str, numeric: bool = False, datetime: bool = False):
            if name not in columns:
                raise AgentInvalidPlanError(f"Unknown Dataset column '{name}'.")
            semantic = columns[name].upper()
            if numeric and not any(x in semantic for x in ("NUMERIC", "INT", "FLOAT", "DOUBLE", "DECIMAL")):
                raise AgentInvalidPlanError(f"Column '{name}' must be numeric.")
            if datetime and not any(x in semantic for x in ("DATETIME", "DATE", "TIME")):
                raise AgentInvalidPlanError(f"Column '{name}' must be datetime.")

        if step.tool == "CHART":
            spec = step.input.spec
            if isinstance(spec, (BarSpec, PieSpec)):
                require(spec.category)
                require(spec.metric, spec.aggregation != "count")
            elif isinstance(spec, LineSpec):
                require(spec.x, datetime=bool(spec.frequency))
                require(spec.y, spec.aggregation != "count")
                spec.series and require(spec.series)
            elif isinstance(spec, ScatterSpec):
                require(spec.x, True)
                require(spec.y, True)
                spec.series and require(spec.series)
            elif isinstance(spec, HistogramSpec):
                require(spec.column, True)
            elif isinstance(spec, BoxplotSpec):
                require(spec.value, True)
                spec.category and require(spec.category)
        elif step.tool == "ANALYSIS":
            known = set(columns)
            for op in step.input.plan.operations:
                payload = op.model_dump()
                for key in ("column", "datetime_column"):
                    if isinstance(payload.get(key), str) and payload[key] not in known:
                        raise AgentInvalidPlanError(f"Unknown Dataset column '{payload[key]}'.")
                for key in ("columns", "group_by"):
                    for name in payload.get(key) or []:
                        if name not in known:
                            raise AgentInvalidPlanError(f"Unknown Dataset column '{name}'.")
                for metric in payload.get("metrics", []):
                    if metric["column"] not in known:
                        raise AgentInvalidPlanError(f"Unknown Dataset column '{metric['column']}'.")
                if payload.get("metric") and payload["metric"]["column"] not in known:
                    raise AgentInvalidPlanError(f"Unknown Dataset column '{payload['metric']['column']}'.")
                if op.type == "derive_column":
                    known.add(op.name)
