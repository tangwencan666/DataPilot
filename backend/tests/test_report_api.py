from io import BytesIO
from app.api import get_llm_provider
from app.main import app
from app.agents.schemas import AgentFinalResponse, AgentPlan
from app.query.schemas import SQLGenerationResult


class Provider:
    is_configured = True

    def __init__(self, mode="ok"):
        self.mode = mode

    def generate_plan(self, q, c):
        return AgentPlan.model_validate(
            {
                "goal": "Sales report",
                "summary": "Analyze sales",
                "steps": [
                    {
                        "id": "sql_1",
                        "tool": "SQL",
                        "purpose": "Sales totals",
                        "depends_on": [],
                        "input": {"question": "sales totals"},
                        "expected_output": "totals",
                    }
                ],
            }
        )

    def generate_sql(self, q, c):
        return SQLGenerationResult(
            sql="SELECT region, SUM(sales) total FROM dataset GROUP BY region", explanation="Regional totals", confidence=1, assumptions=[]
        )

    def generate_final_summary(self, *a):
        return AgentFinalResponse(answer="Sales analyzed", key_findings=["North leads"], limitations=[], used_tools=[], artifacts=[])

    def generate_insights(self, e):
        ref = "artifact:fake" if self.mode == "badref" else "step:sql_1"
        return {
            "insights": [
                {
                    "id": "i1",
                    "title": "<script>alert(1)</script>",
                    "statement": "North <b>leads</b>",
                    "importance": "HIGH",
                    "confidence": 0.9,
                    "evidence_refs": [ref],
                    "limitations": [],
                }
            ]
        }

    def compose_report(self, e, i):
        return {
            "title": "Sales <script>Report</script>",
            "executive_summary": "Summary <iframe>x</iframe>",
            "detailed_analysis": "Details onclick=evil",
            "conclusion": "Done javascript:bad",
            "limitations": [],
        }


def upload(client, name="sales.csv"):
    return client.post("/api/v1/datasets", files={"file": (name, BytesIO(b"region,sales\nNorth,30\nSouth,20\n"), "text/csv")}).json()["id"]


def agent(client, d):
    app.dependency_overrides[get_llm_provider] = lambda: Provider()
    return client.post(f"/api/v1/datasets/{d}/agent-runs", json={"question": "Analyze"}).json()["run"]["id"]


def test_report_crud_history_and_persistence(client):
    d = upload(client)
    r = agent(client, d)
    created = client.post(f"/api/v1/datasets/{d}/reports", json={"agent_run_id": r})
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "READY" and body["insight_count"] == 1
    rid = body["id"]
    assert client.get(f"/api/v1/datasets/{d}/reports").json()["total"] == 1
    assert client.get(f"/api/v1/datasets/{d}/reports/{rid}").json()["report"]["key_insights"][0]["evidence_refs"] == ["step:sql_1"]
    assert client.delete(f"/api/v1/datasets/{d}/reports/{rid}").status_code == 204


def test_markdown_export_utf8_and_escaping(client):
    d = upload(client)
    rid = client.post(f"/api/v1/datasets/{d}/reports", json={"agent_run_id": agent(client, d)}).json()["id"]
    text = client.get(f"/api/v1/datasets/{d}/reports/{rid}/export?format=markdown").text
    assert "# Sales" in text and "<script>" not in text and "&lt;script&gt;" in text


def test_html_export_is_escaped_and_has_no_active_content(client):
    d = upload(client)
    rid = client.post(f"/api/v1/datasets/{d}/reports", json={"agent_run_id": agent(client, d)}).json()["id"]
    text = client.get(f"/api/v1/datasets/{d}/reports/{rid}/export?format=html").text.lower()
    assert "<script>" not in text and "<iframe>" not in text and "onclick=" not in text and "javascript:" not in text


def test_unsupported_export(client):
    d = upload(client)
    rid = client.post(f"/api/v1/datasets/{d}/reports", json={"agent_run_id": agent(client, d)}).json()["id"]
    response = client.get(f"/api/v1/datasets/{d}/reports/{rid}/export?format=pdf")
    assert response.status_code == 422 and response.json()["code"] == "REPORT_UNSUPPORTED_FORMAT"


def test_failed_source_rejected(client):
    d = upload(client)
    from app.config import get_settings, Settings

    app.dependency_overrides[get_settings] = lambda: Settings(
        upload_dir="data/uploads", llm_api_key="x", llm_model="x", agent_timeout_seconds=0
    )
    r = agent(client, d)
    response = client.post(f"/api/v1/datasets/{d}/reports", json={"agent_run_id": r})
    assert response.status_code == 422 and response.json()["code"] == "REPORT_SOURCE_NOT_READY"


def test_source_not_found(client):
    d = upload(client)
    app.dependency_overrides[get_llm_provider] = lambda: Provider()
    response = client.post(f"/api/v1/datasets/{d}/reports", json={"agent_run_id": "missing"})
    assert response.status_code == 404


def test_dataset_mismatch(client):
    d1 = upload(client, "a.csv")
    r = agent(client, d1)
    d2 = upload(client, "b.csv")
    response = client.post(f"/api/v1/datasets/{d2}/reports", json={"agent_run_id": r})
    assert response.status_code == 422 and response.json()["code"] == "REPORT_DATASET_MISMATCH"


def test_llm_unconfigured(client):
    class Missing:
        is_configured = False

    d = upload(client)
    r = agent(client, d)
    app.dependency_overrides[get_llm_provider] = lambda: Missing()
    response = client.post(f"/api/v1/datasets/{d}/reports", json={"agent_run_id": r})
    assert response.status_code == 503


def test_invalid_evidence_ref(client):
    d = upload(client)
    r = agent(client, d)
    app.dependency_overrides[get_llm_provider] = lambda: Provider("badref")
    response = client.post(f"/api/v1/datasets/{d}/reports", json={"agent_run_id": r})
    assert response.status_code == 422 and response.json()["code"] == "REPORT_INVALID_INSIGHTS"


def test_report_not_found(client):
    d = upload(client)
    app.dependency_overrides[get_llm_provider] = lambda: Provider()
    assert client.get(f"/api/v1/datasets/{d}/reports/missing").status_code == 404
