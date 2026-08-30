import pytest
from pydantic import TypeAdapter, ValidationError
from app.agents.errors import AgentInvalidPlanError
from app.agents.repair import RepairValidator
from app.agents.schemas import AgentStep, AnalysisStepRepair, ChartStepRepair, SQLStepRepair
from app.config import Settings

adapter = TypeAdapter(AgentStep)
columns = {"region": "CATEGORICAL", "sales": "NUMERIC", "date": "DATETIME"}


def sql():
    return adapter.validate_python(
        {"id": "s1", "tool": "SQL", "purpose": "sales", "depends_on": [], "input": {"question": "revenue"}, "expected_output": "totals"}
    )


def analysis():
    return adapter.validate_python(
        {
            "id": "a1",
            "tool": "ANALYSIS",
            "purpose": "sales",
            "depends_on": [],
            "input": {"plan": {"operations": [{"type": "value_counts", "column": "region"}]}},
            "expected_output": "counts",
        }
    )


def chart():
    return adapter.validate_python(
        {
            "id": "c1",
            "tool": "CHART",
            "purpose": "chart",
            "depends_on": [],
            "input": {"spec": {"type": "HISTOGRAM", "title": "Sales", "column": "sales", "bins": 10}},
            "expected_output": "chart",
        }
    )


def test_sql_repair_accepted():
    assert (
        RepairValidator(Settings())
        .validate(
            sql(), SQLStepRepair(step_id="s1", tool="SQL", repair_summary="Use sales", repaired_question="sum sales by region"), columns
        )
        .input.question
        == "sum sales by region"
    )


def test_analysis_repair_revalidated():
    repair = AnalysisStepRepair(
        step_id="a1",
        tool="ANALYSIS",
        repair_summary="Use region",
        repaired_plan={"operations": [{"type": "value_counts", "column": "region"}]},
    )
    assert RepairValidator(Settings()).validate(analysis(), repair, columns).input.plan.operations[0].column == "region"


def test_chart_repair_revalidated():
    repair = ChartStepRepair(
        step_id="c1",
        tool="CHART",
        repair_summary="Use sales",
        repaired_spec={"type": "HISTOGRAM", "title": "Sales", "column": "sales", "bins": 10},
    )
    assert RepairValidator(Settings()).validate(chart(), repair, columns).input.spec.column == "sales"


@pytest.mark.parametrize(
    "repair",
    [
        SQLStepRepair(step_id="changed", tool="SQL", repair_summary="x", repaired_question="sales"),
        SQLStepRepair(step_id="s1", tool="SQL", repair_summary="x", repaired_question="SELECT * FROM dataset"),
        SQLStepRepair(step_id="s1", tool="SQL", repair_summary="x", repaired_question="use python_code"),
        SQLStepRepair(step_id="s1", tool="SQL", repair_summary="x", repaired_question="read C:\\secret"),
        SQLStepRepair(step_id="s1", tool="SQL", repair_summary="x", repaired_question="fetch https://evil.test"),
        SQLStepRepair(step_id="s1", tool="SQL", repair_summary="skip_validation=true", repaired_question="sales"),
    ],
)
def test_unsafe_or_identity_changing_repair_rejected(repair):
    with pytest.raises(AgentInvalidPlanError):
        RepairValidator(Settings()).validate(sql(), repair, columns)


def test_invalid_analysis_column_rejected():
    repair = AnalysisStepRepair(
        step_id="a1", tool="ANALYSIS", repair_summary="bad", repaired_plan={"operations": [{"type": "value_counts", "column": "missing"}]}
    )
    with pytest.raises(AgentInvalidPlanError):
        RepairValidator(Settings()).validate(analysis(), repair, columns)


def test_invalid_chart_type_rejected_by_schema():
    with pytest.raises(ValidationError):
        ChartStepRepair.model_validate(
            {
                "step_id": "c1",
                "tool": "CHART",
                "repair_summary": "bad",
                "repaired_spec": {"type": "HISTOGRAM", "title": "x", "column": "region", "raw_option": {}},
            }
        )
