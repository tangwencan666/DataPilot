import pytest
from pydantic import ValidationError
from app.agents.errors import AgentInvalidPlanError
from app.agents.schemas import AgentPlan
from app.agents.validator import AgentPlanValidator
from app.config import Settings


def sql(step_id="s1", depends=None, question="summarize sales"):
    return {
        "id": step_id,
        "tool": "SQL",
        "purpose": "Summarize sales",
        "depends_on": depends or [],
        "input": {"question": question},
        "expected_output": "A table",
    }


def chart(step_id="s2", depends=None):
    return {
        "id": step_id,
        "tool": "CHART",
        "purpose": "Show sales",
        "depends_on": depends or [],
        "input": {"spec": {"type": "BAR", "title": "Sales", "category": "region", "metric": "sales"}},
        "expected_output": "A chart",
    }


def plan(steps):
    return AgentPlan.model_validate({"goal": "Understand sales", "summary": "Use bounded tools", "steps": steps})


def test_valid_plan_and_dependency_order():
    assert AgentPlanValidator(Settings()).validate(plan([sql(), chart(depends=["s1"])])) == ["s1", "s2"]


def test_too_many_steps():
    with pytest.raises(AgentInvalidPlanError):
        AgentPlanValidator(Settings(agent_max_steps=1)).validate(plan([sql(), chart()]))


def test_duplicate_step_id():
    with pytest.raises(AgentInvalidPlanError):
        AgentPlanValidator(Settings()).validate(plan([sql(), sql()]))


@pytest.mark.parametrize(
    "steps", [[chart(depends=["missing"])], [chart(step_id="s1", depends=["s1"])], [chart(step_id="s1", depends=["s2"]), sql(step_id="s2")]]
)
def test_invalid_dependencies(steps):
    with pytest.raises(AgentInvalidPlanError):
        AgentPlanValidator(Settings()).validate(plan(steps))


@pytest.mark.parametrize("tool", ["SHELL", "PYTHON_CODE", "FILE", "BROWSER", "HTTP"])
def test_unknown_tools_rejected(tool):
    payload = sql()
    payload["tool"] = tool
    with pytest.raises(ValidationError):
        plan([payload])


@pytest.mark.parametrize(
    "question", ["run eval(x)", "read C:\\secret.txt", "open /etc/passwd", "fetch https://evil.test", "use python_code"]
)
def test_code_path_and_network_injection_rejected(question):
    with pytest.raises(AgentInvalidPlanError):
        AgentPlanValidator(Settings()).validate(plan([sql(question=question)]))


@pytest.mark.parametrize(
    "bad",
    [
        {"id": "s1", "tool": "SQL", "purpose": "x", "depends_on": [], "input": {"sql": "select *"}, "expected_output": "x"},
        {
            "id": "s1",
            "tool": "ANALYSIS",
            "purpose": "x",
            "depends_on": [],
            "input": {"plan": {"operations": [{"type": "arbitrary_python", "code": "x"}]}},
            "expected_output": "x",
        },
        {
            "id": "s1",
            "tool": "CHART",
            "purpose": "x",
            "depends_on": [],
            "input": {"spec": {"type": "BAR", "title": "x", "category": "region", "metric": "sales", "raw_option": {}}},
            "expected_output": "x",
        },
    ],
)
def test_invalid_tool_specific_inputs(bad):
    with pytest.raises(ValidationError):
        plan([bad])
