from typing import Protocol
from app.agents.schemas import AnalysisAgentStep, ChartAgentStep, SQLAgentStep, ToolExecutionResult, ToolName
from app.analysis.service import StructuredAnalysisService
from app.charts.service import ChartService
from app.query.service import NaturalLanguageSQLService


class AgentTool(Protocol):
    name: ToolName

    def execute(self, dataset_id: str, step) -> ToolExecutionResult: ...


class SQLToolAdapter:
    name = ToolName.SQL

    def __init__(self, service: NaturalLanguageSQLService, max_rows: int, max_cells: int) -> None:
        self.service = service
        self.max_rows = max_rows
        self.max_cells = max_cells

    def execute(self, dataset_id: str, step: SQLAgentStep) -> ToolExecutionResult:
        response = self.service.run(dataset_id, step.input.question)
        rows = response.result.rows[: self.max_rows]
        cell_limit = max(1, self.max_cells // max(1, len(response.result.columns)))
        rows = rows[:cell_limit]
        return ToolExecutionResult(
            tool=self.name,
            status="SUCCEEDED",
            summary=response.generation.explanation,
            columns=response.result.columns,
            rows=rows,
            row_count=response.result.row_count,
            truncated=response.result.truncated or len(rows) < len(response.result.rows),
            metadata={"generated_sql": response.result.sql, "execution_time_ms": response.result.execution_time_ms},
            artifact_type="query",
            artifact_id=response.query.id,
        )


class AnalysisToolAdapter:
    name = ToolName.ANALYSIS

    def __init__(self, service: StructuredAnalysisService, max_rows: int, max_cells: int) -> None:
        self.service = service
        self.max_rows = max_rows
        self.max_cells = max_cells

    def execute(self, dataset_id: str, step: AnalysisAgentStep) -> ToolExecutionResult:
        response = self.service.execute(dataset_id, step.input.plan)
        rows = response.result.rows[: self.max_rows]
        rows = rows[: max(1, self.max_cells // max(1, len(response.result.columns)))]
        return ToolExecutionResult(
            tool=self.name,
            status="SUCCEEDED",
            summary=f"Completed {len(response.result.operations_executed)} controlled analysis operations.",
            columns=response.result.columns,
            rows=rows,
            row_count=response.result.row_count,
            truncated=response.result.truncated or len(rows) < len(response.result.rows),
            warnings=response.result.warnings,
            metadata={"operations_executed": [x.model_dump() for x in response.result.operations_executed]},
            artifact_type="analysis",
            artifact_id=response.analysis.id,
        )


class ChartToolAdapter:
    name = ToolName.CHART

    def __init__(self, service: ChartService) -> None:
        self.service = service

    def execute(self, dataset_id: str, step: ChartAgentStep) -> ToolExecutionResult:
        response = self.service.create(dataset_id, step.input.spec)
        return ToolExecutionResult(
            tool=self.name,
            status="SUCCEEDED",
            summary=f"Created {response.type} chart '{response.title}'.",
            row_count=response.rendered_point_count,
            truncated=False,
            warnings=response.warnings,
            metadata={
                "chart_type": response.type,
                "source_row_count": response.source_row_count,
                "rendered_point_count": response.rendered_point_count,
                "sampled": response.sampled,
            },
            artifact_type="chart",
            artifact_id=response.chart_id,
        )


class ToolRegistry:
    def __init__(self, tools: list[AgentTool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def get(self, name: ToolName) -> AgentTool:
        if name not in self._tools:
            raise KeyError(f"Tool {name} is not registered")
        return self._tools[name]

    @property
    def names(self) -> list[ToolName]:
        return list(self._tools)
