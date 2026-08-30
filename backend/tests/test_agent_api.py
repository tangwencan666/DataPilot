from io import BytesIO
from app.api import get_llm_provider
from app.config import Settings, get_settings
from app.exceptions import LLMProviderError, QueryError
from app.agents.schemas import AgentFinalResponse, AgentPlan
from app.main import app
from app.query.schemas import SQLGenerationResult


class FakeAgentProvider:
    is_configured = True

    def __init__(self, mode="SQL"):
        self.mode = mode

    def generate_sql(self, question, schema_context):
        if question == "force invalid column":
            error = QueryError("Column revenue does not exist.")
            error.code = "QUERY_INVALID_COLUMN"
            raise error
        if question == "force failure":
            raise LLMProviderError("Tool failed.")
        return SQLGenerationResult(
            sql="SELECT region, SUM(sales) AS total FROM dataset GROUP BY region ORDER BY total DESC",
            explanation="Sales grouped by region.",
            confidence=1,
            assumptions=[],
        )

    def generate_plan(self, question, context):
        if self.mode in ("SQL", "BADFINAL"):
            steps = [
                {
                    "id": "sql_1",
                    "tool": "SQL",
                    "purpose": "Group sales by region",
                    "depends_on": [],
                    "input": {"question": "sales by region"},
                    "expected_output": "Regional totals",
                }
            ]
        elif self.mode == "ANALYSIS":
            steps = [
                {
                    "id": "analysis_1",
                    "tool": "ANALYSIS",
                    "purpose": "Group sales",
                    "depends_on": [],
                    "input": {
                        "plan": {
                            "operations": [
                                {
                                    "type": "groupby_aggregate",
                                    "group_by": ["region"],
                                    "metrics": [{"column": "sales", "aggregation": "sum"}],
                                }
                            ]
                        }
                    },
                    "expected_output": "Regional totals",
                }
            ]
        elif self.mode == "CHART":
            steps = [
                {
                    "id": "chart_1",
                    "tool": "CHART",
                    "purpose": "Chart sales",
                    "depends_on": [],
                    "input": {"spec": {"type": "BAR", "title": "Sales by region", "category": "region", "metric": "sales"}},
                    "expected_output": "Bar chart",
                }
            ]
        elif self.mode == "CHAIN":
            steps = [
                {
                    "id": "sql_1",
                    "tool": "SQL",
                    "purpose": "Group sales",
                    "depends_on": [],
                    "input": {"question": "sales by region"},
                    "expected_output": "Totals",
                },
                {
                    "id": "chart_1",
                    "tool": "CHART",
                    "purpose": "Chart sales",
                    "depends_on": ["sql_1"],
                    "input": {"spec": {"type": "BAR", "title": "Sales", "category": "region", "metric": "sales"}},
                    "expected_output": "Chart",
                },
            ]
        elif self.mode == "RETRY":
            steps = [
                {
                    "id": "sql",
                    "tool": "SQL",
                    "purpose": "Repair SQL question",
                    "depends_on": [],
                    "input": {"question": "force invalid column"},
                    "expected_output": "totals",
                }
            ]
        elif self.mode == "PARTIAL":
            steps = [
                {
                    "id": "sql",
                    "tool": "SQL",
                    "purpose": "Succeed",
                    "depends_on": [],
                    "input": {"question": "sales by region"},
                    "expected_output": "x",
                },
                {
                    "id": "bad",
                    "tool": "SQL",
                    "purpose": "Fail independently",
                    "depends_on": [],
                    "input": {"question": "force failure"},
                    "expected_output": "x",
                },
            ]
        elif self.mode == "INVALID":
            steps = [
                {
                    "id": f"s{i}",
                    "tool": "SQL",
                    "purpose": "Too many",
                    "depends_on": [],
                    "input": {"question": "sales"},
                    "expected_output": "x",
                }
                for i in range(9)
            ]
        elif self.mode == "LLMERROR":
            raise LLMProviderError("Planner timed out.")
        else:
            steps = [
                {
                    "id": "bad",
                    "tool": "SQL",
                    "purpose": "Fail",
                    "depends_on": [],
                    "input": {"question": "force failure"},
                    "expected_output": "x",
                },
                {
                    "id": "dependent",
                    "tool": "SQL",
                    "purpose": "Skip",
                    "depends_on": ["bad"],
                    "input": {"question": "sales by region"},
                    "expected_output": "x",
                },
            ]
        return AgentPlan.model_validate({"goal": "Analyze sales", "summary": "Use controlled tools.", "steps": steps})

    def generate_final_summary(self, question, plan_summary, step_summaries):
        if self.mode == "BADFINAL":
            return {"answer": "", "unknown": "bad"}
        return AgentFinalResponse(
            answer="Regional sales were analyzed.",
            key_findings=["North leads."],
            limitations=["Dataset only."],
            used_tools=[],
            artifacts=[],
        )

    def generate_step_repair(self, tool, bounded_input):
        return {
            "step_id": "sql",
            "tool": "SQL",
            "repair_summary": "Changed the sub-question to use sales and region.",
            "repaired_question": "sales by region",
        }


def upload(client):
    return client.post(
        "/api/v1/datasets",
        files={
            "file": (
                "sales.csv",
                BytesIO(b"region,sales,date\nNorth,30,2024-01-01\nSouth,20,2024-02-01\nNorth,10,2024-03-01\n"),
                "text/csv",
            )
        },
    ).json()["id"]


def run(client, dataset_id, mode):
    app.dependency_overrides[get_llm_provider] = lambda: FakeAgentProvider(mode)
    return client.post(f"/api/v1/datasets/{dataset_id}/agent-runs", json={"question": "Analyze sales"})


def test_sql_agent_run_and_history(client):
    dataset_id = upload(client)
    response = run(client, dataset_id, "SQL")
    assert response.status_code == 201
    body = response.json()
    assert body["run"]["status"] == "SUCCEEDED"
    assert body["run"]["steps"][0]["artifact_type"] == "query"
    assert body["final"]["used_tools"] == ["SQL"]
    history = client.get(f"/api/v1/datasets/{dataset_id}/agent-runs").json()
    assert history["total"] == 1
    detail = client.get(f"/api/v1/datasets/{dataset_id}/agent-runs/{body['run']['id']}")
    assert detail.json()["steps"][0]["status"] == "SUCCEEDED"


def test_analysis_agent_run(client):
    dataset_id = upload(client)
    body = run(client, dataset_id, "ANALYSIS").json()
    assert body["run"]["status"] == "SUCCEEDED"
    assert body["run"]["steps"][0]["artifact_type"] == "analysis"


def test_chart_agent_run(client):
    dataset_id = upload(client)
    body = run(client, dataset_id, "CHART").json()
    assert body["run"]["status"] == "SUCCEEDED"
    assert body["run"]["steps"][0]["artifact_type"] == "chart"
    assert body["final"]["artifacts"][0]["type"] == "chart"


def test_sequential_dependency_run(client):
    dataset_id = upload(client)
    body = run(client, dataset_id, "CHAIN").json()
    assert body["run"]["completed_step_count"] == 2
    assert [x["status"] for x in body["run"]["steps"]] == ["SUCCEEDED", "SUCCEEDED"]


def test_failure_skips_dependent_step(client):
    dataset_id = upload(client)
    body = run(client, dataset_id, "FAIL").json()
    assert body["run"]["status"] == "FAILED"
    assert [x["status"] for x in body["run"]["steps"]] == ["FAILED", "SKIPPED"]


def test_missing_agent_and_dataset(client):
    app.dependency_overrides[get_llm_provider] = lambda: FakeAgentProvider()
    assert client.get("/api/v1/datasets/missing/agent-runs").status_code == 404
    dataset_id = upload(client)
    assert client.get(f"/api/v1/datasets/{dataset_id}/agent-runs/missing").status_code == 404


def test_agent_llm_not_configured(client):
    class Missing:
        is_configured = False

    app.dependency_overrides[get_llm_provider] = lambda: Missing()
    dataset_id = upload(client)
    response = client.post(f"/api/v1/datasets/{dataset_id}/agent-runs", json={"question": "Analyze"})
    assert response.status_code == 503 and response.json()["code"] == "AGENT_LLM_NOT_CONFIGURED"


def test_partial_result_when_independent_step_fails(client):
    dataset_id = upload(client)
    body = run(client, dataset_id, "PARTIAL").json()
    assert body["run"]["status"] == "PARTIAL"
    assert body["run"]["completed_step_count"] == 1
    assert body["final"] is not None


def test_invalid_final_synthesis_is_persisted_as_partial(client):
    dataset_id = upload(client)
    body = run(client, dataset_id, "BADFINAL").json()
    assert body["run"]["status"] == "PARTIAL"
    assert body["run"]["error_code"] == "AGENT_FINAL_SYNTHESIS_FAILED"
    assert body["final"] is None


def test_too_many_planner_steps_rejected(client):
    dataset_id = upload(client)
    response = run(client, dataset_id, "INVALID")
    assert response.status_code == 422 and response.json()["code"] == "AGENT_INVALID_PLAN"


def test_planner_provider_error(client):
    dataset_id = upload(client)
    response = run(client, dataset_id, "LLMERROR")
    assert response.status_code == 502 and response.json()["code"] == "AGENT_LLM_ERROR"


def test_agent_total_timeout_stops_new_steps(client, upload_dir):
    app.dependency_overrides[get_settings] = lambda: Settings(
        database_url="sqlite://", upload_dir=upload_dir, llm_api_key="fake", llm_model="fake", agent_timeout_seconds=0
    )
    dataset_id = upload(client)
    body = run(client, dataset_id, "SQL").json()
    assert body["run"]["status"] == "FAILED"
    assert body["run"]["steps"][0]["error_code"] == "AGENT_TIMEOUT"


def test_controlled_retry_persists_attempt_trace(client):
    dataset_id = upload(client)
    body = run(client, dataset_id, "RETRY").json()
    step = body["run"]["steps"][0]
    assert body["run"]["status"] == "SUCCEEDED" and step["attempt_count"] == 2 and step["repair_count"] == 1
    assert [x["attempt_type"] for x in step["attempts"]] == ["INITIAL", "REPAIR"]
    assert step["attempts"][0]["observation_json"]["error_category"] == "INVALID_COLUMN"
    assert step["attempts"][1]["repair_summary_json"]["summary"]
    detail = client.get(f"/api/v1/datasets/{dataset_id}/agent-runs/{body['run']['id']}").json()
    assert len(detail["steps"][0]["attempts"]) == 2
