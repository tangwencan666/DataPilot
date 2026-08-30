from pathlib import Path

from fastapi.testclient import TestClient

from app.analysis.executor import PandasAnalysisExecutor
from app.analysis.process import AnalysisProcessRunner, _test_sleep_worker
from app.analysis.schemas import AnalysisPlan
from app.api import get_analysis_runner
from app.config import Settings
from app.main import app
from app.parsers import load_dataframe


class DirectRunner:
    def run(self, payload):
        frame, _ = load_dataframe(Path(payload["path"]).read_bytes(), payload["file_type"])
        return PandasAnalysisExecutor(Settings(**payload["settings"])).execute(
            frame, AnalysisPlan.model_validate(payload["plan"]), payload["sampled"]
        )


def upload(client: TestClient) -> dict:
    return client.post("/api/v1/datasets", files={"file": ("sales.csv", b"region,sales\nEast,10\nEast,20\nWest,5\n", "text/csv")}).json()


def plan():
    return {
        "operations": [
            {
                "type": "groupby_aggregate",
                "group_by": ["region"],
                "metrics": [{"column": "sales", "aggregation": "sum"}],
                "sort": [{"column": "sales_sum", "direction": "desc"}],
            }
        ]
    }


def test_analysis_success_history_and_detail(client: TestClient) -> None:
    app.dependency_overrides[get_analysis_runner] = lambda: DirectRunner()
    dataset = upload(client)
    response = client.post(f"/api/v1/datasets/{dataset['id']}/analyses", json=plan())
    assert response.status_code == 200
    body = response.json()
    assert body["result"]["rows"][0] == ["East", 30]
    assert body["analysis"]["status"] == "SUCCEEDED"
    listing = client.get(f"/api/v1/datasets/{dataset['id']}/analyses?page=1&page_size=1").json()
    assert listing["total"] == 1
    assert client.get(f"/api/v1/datasets/{dataset['id']}/analyses/{body['analysis']['id']}").status_code == 200


def test_analysis_validation_and_dataset_errors(client: TestClient) -> None:
    app.dependency_overrides[get_analysis_runner] = lambda: DirectRunner()
    assert client.post("/api/v1/datasets/missing/analyses", json=plan()).status_code == 404
    dataset = upload(client)
    invalid = client.post(f"/api/v1/datasets/{dataset['id']}/analyses", json={"operations": [{"type": "python", "code": "import os"}]})
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "VALIDATION_ERROR"


def test_timeout_status_and_subsequent_recovery(client: TestClient) -> None:
    dataset = upload(client)
    timeout_settings = Settings(database_url="sqlite://", analysis_timeout_seconds=0.1)
    app.dependency_overrides[get_analysis_runner] = lambda: AnalysisProcessRunner(timeout_settings, _test_sleep_worker)
    response = client.post(f"/api/v1/datasets/{dataset['id']}/analyses", json=plan())
    assert response.status_code == 408
    history = client.get(f"/api/v1/datasets/{dataset['id']}/analyses").json()
    assert history["items"][0]["status"] == "TIMED_OUT"
    app.dependency_overrides[get_analysis_runner] = lambda: DirectRunner()
    assert client.post(f"/api/v1/datasets/{dataset['id']}/analyses", json=plan()).status_code == 200
