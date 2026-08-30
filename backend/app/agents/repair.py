import json
import re
from pydantic import TypeAdapter
from app.agents.errors import AgentInvalidPlanError
from app.agents.schemas import (
    AnalysisAgentStep,
    AnalysisStepInput,
    AnalysisStepRepair,
    ChartAgentStep,
    ChartStepInput,
    ChartStepRepair,
    SQLAgentStep,
    SQLStepInput,
    SQLStepRepair,
    StepRepair,
    ToolObservation,
)
from app.agents.validator import FORBIDDEN, AgentPlanValidator
from app.config import Settings


class RepairValidator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def validate(self, original, repair: StepRepair, columns: dict[str, str] | None = None):
        if repair.step_id != original.id or repair.tool != original.tool:
            raise AgentInvalidPlanError("Repair must preserve step id and tool.")
        payload = json.dumps(repair.model_dump(mode="json"), ensure_ascii=False).lower()
        if any(token in payload for token in FORBIDDEN) or "skip_validation" in payload or "raw_sql" in payload or "raw_echarts" in payload:
            raise AgentInvalidPlanError("Repair contains forbidden input.")
        if isinstance(repair, SQLStepRepair) and re.match(
            r"\s*(select|with|insert|update|delete|drop|alter|create)\b", repair.repaired_question, re.I
        ):
            raise AgentInvalidPlanError("SQL repair must be a natural-language question, not raw SQL.")
        if isinstance(repair, SQLStepRepair):
            new = original.model_copy(update={"input": SQLStepInput(question=repair.repaired_question)})
        elif isinstance(repair, AnalysisStepRepair):
            new = original.model_copy(update={"input": AnalysisStepInput(plan=repair.repaired_plan)})
        elif isinstance(repair, ChartStepRepair):
            new = original.model_copy(update={"input": ChartStepInput(spec=repair.repaired_spec)})
        else:
            raise AgentInvalidPlanError("Unsupported repair.")
        from app.agents.schemas import AgentPlan

        AgentPlanValidator(self.settings).validate(
            AgentPlan(goal="repair validation", summary="repair validation", steps=[new.model_copy(update={"depends_on": []})]), columns
        )
        return new


class StepRepairService:
    def __init__(self, provider, settings: Settings) -> None:
        self.provider = provider
        self.settings = settings

    def repair(self, user_question: str, plan_summary: str, step, observation: ToolObservation, context: dict):
        bounded = {
            "user_question": user_question[:2000],
            "plan_summary": plan_summary[:1000],
            "step": step.model_dump(mode="json"),
            "observation": observation.model_dump(mode="json"),
            "dataset_context": context,
        }
        encoded = json.dumps(bounded, ensure_ascii=False, default=str)[: self.settings.agent_repair_context_chars]
        result = self.provider.generate_step_repair(step.tool, encoded)
        return TypeAdapter(StepRepair).validate_python(result)
