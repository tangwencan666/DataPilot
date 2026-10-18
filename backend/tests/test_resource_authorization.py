"""HTTP authorization regressions; all records and model responses are test-only."""

import pytest

from app.api import get_llm_provider
from app.config import get_settings
from app.main import app
from tests.test_report_api import Provider


@pytest.fixture
def owned_resources(client):
    settings = app.dependency_overrides[get_settings]().model_copy(update={"auth_required": True})
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_llm_provider] = lambda: Provider()

    def register(email):
        response = client.post("/api/v1/auth/register", json={"email": email, "password": "test-password-only"})
        assert response.status_code == 201
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    owner = register("owner@example.com")
    other = register("other@example.com")

    def upload(headers, filename):
        response = client.post(
            "/api/v1/datasets",
            headers=headers,
            files={"file": (filename, b"region,sales\nNorth,30\nSouth,20\n", "text/csv")},
        )
        assert response.status_code == 201
        return response.json()["id"]

    dataset = upload(owner, "owner.csv")
    sibling = upload(owner, "sibling.csv")
    foreign = upload(other, "other.csv")
    base = f"/api/v1/datasets/{dataset}"
    response = client.post(base + "/agent-runs", headers=owner, json={"question": "Analyze regional sales"})
    assert response.status_code == 201
    run = response.json()["run"]
    response = client.post(base + "/reports", headers=owner, json={"agent_run_id": run["id"]})
    assert response.status_code == 201
    report = response.json()["id"]
    response = client.post(
        base + "/charts",
        headers=owner,
        json={
            "type": "BAR",
            "title": "Regional sales",
            "category": "region",
            "metric": "sales",
            "aggregation": "sum",
        },
    )
    assert response.status_code == 201
    chart = response.json()["chart_id"]
    response = client.post(base + "/analyses", headers=owner, json={"operations": [{"type": "value_counts", "column": "region"}]})
    assert response.status_code == 200
    return {
        "owner": owner,
        "other": other,
        "dataset": dataset,
        "sibling": sibling,
        "foreign": foreign,
        "base": base,
        "report": report,
        "agent_run": run["id"],
        "query": run["steps"][0]["artifact_id"],
        "chart": chart,
        "analysis": response.json()["analysis"]["id"],
    }


REPORT_ACTIONS = [("GET", ""), ("GET", "/export?format=markdown"), ("GET", "/export?format=html"), ("DELETE", "")]


def test_owner_report_read_export_and_delete(client, owned_resources):
    r = owned_resources
    path = f"{r['base']}/reports/{r['report']}"
    response = client.get(path, headers=r["owner"])
    assert response.status_code == 200
    assert response.json()["id"] == r["report"]
    assert response.json()["dataset_id"] == r["dataset"]
    for fmt in ("markdown", "html"):
        exported = client.get(path + f"/export?format={fmt}", headers=r["owner"])
        assert exported.status_code == 200 and "Sales" in exported.text
    assert client.delete(path, headers=r["owner"]).status_code == 204
    assert client.get(path, headers=r["owner"]).status_code == 404


@pytest.mark.parametrize("method,suffix", REPORT_ACTIONS)
def test_other_user_cannot_access_report(client, owned_resources, method, suffix):
    r = owned_resources
    path = f"{r['base']}/reports/{r['report']}"
    response = client.request(method, path + suffix, headers=r["other"])
    assert response.status_code == 404
    assert response.json()["code"] == "REPORT_SOURCE_NOT_FOUND"
    assert "Sales" not in response.text and r["report"] not in response.text
    # In particular, a denied DELETE must not remove the owner's resource.
    assert client.get(path, headers=r["owner"]).status_code == 200


@pytest.mark.parametrize("method,suffix", REPORT_ACTIONS)
def test_missing_report_returns_not_found(client, owned_resources, method, suffix):
    r = owned_resources
    response = client.request(method, r["base"] + "/reports/not-a-report" + suffix, headers=r["owner"])
    assert response.status_code == 404
    assert response.json()["code"] == "REPORT_NOT_FOUND"


@pytest.mark.parametrize("parent", ["sibling", "foreign"])
@pytest.mark.parametrize("method,suffix", REPORT_ACTIONS)
def test_report_cannot_be_reparented_in_url(client, owned_resources, parent, method, suffix):
    r = owned_resources
    response = client.request(method, f"/api/v1/datasets/{r[parent]}/reports/{r['report']}" + suffix, headers=r["owner"])
    assert response.status_code == 404
    assert response.json()["code"] == ("REPORT_NOT_FOUND" if parent == "sibling" else "REPORT_SOURCE_NOT_FOUND")
    assert client.get(f"{r['base']}/reports/{r['report']}", headers=r["owner"]).status_code == 200


@pytest.mark.parametrize("method,suffix", REPORT_ACTIONS)
def test_report_requires_authentication_when_enabled(client, owned_resources, method, suffix):
    r = owned_resources
    response = client.request(method, f"{r['base']}/reports/{r['report']}" + suffix)
    assert response.status_code == 401


def test_report_create_cannot_reuse_foreign_agent_run(client, owned_resources):
    r = owned_resources
    response = client.post(f"/api/v1/datasets/{r['foreign']}/reports", headers=r["other"], json={"agent_run_id": r["agent_run"]})
    assert response.status_code == 404
    assert response.json()["code"] == "REPORT_SOURCE_NOT_FOUND"


@pytest.mark.parametrize("suffix", ["queries/{query}", "analyses/{analysis}", "charts/{chart}", "agent-runs/{agent_run}"])
def test_child_detail_checks_owner_and_parent(client, owned_resources, suffix):
    r = owned_resources
    suffix = suffix.format(**r)
    assert client.get(r["base"] + "/" + suffix, headers=r["owner"]).status_code == 200
    assert client.get(r["base"] + "/" + suffix, headers=r["other"]).status_code == 404
    assert client.get(f"/api/v1/datasets/{r['sibling']}/" + suffix, headers=r["owner"]).status_code == 404


@pytest.mark.parametrize("suffix", ["", "/preview", "/profile", "/queries", "/analyses", "/charts", "/agent-runs", "/reports"])
def test_other_user_cannot_read_dataset_or_collections(client, owned_resources, suffix):
    r = owned_resources
    response = client.get(r["base"] + suffix, headers=r["other"])
    assert response.status_code == 404
    assert client.get("/api/v1/datasets", headers=r["other"]).json()["total"] == 1


@pytest.mark.parametrize(
    "suffix,payload",
    [
        ("/profile", None),
        ("/queries", {"question": "How many rows?"}),
        ("/analyses", {"operations": [{"type": "value_counts", "column": "region"}]}),
        ("/charts", {"type": "BAR", "title": "Denied", "category": "region", "metric": "sales", "aggregation": "sum"}),
        ("/agent-runs", {"question": "Analyze"}),
        ("/reports", None),
    ],
)
def test_other_user_cannot_create_child_resources(client, owned_resources, suffix, payload):
    r = owned_resources
    if suffix == "/reports":
        payload = {"agent_run_id": r["agent_run"]}
    response = client.post(r["base"] + suffix, headers=r["other"], json=payload)
    assert response.status_code == 404


@pytest.mark.parametrize("suffix", ["", "/charts/{chart}"])
def test_other_user_cannot_delete_dataset_or_chart(client, owned_resources, suffix):
    r = owned_resources
    path = r["base"] + suffix.format(**r)
    assert client.delete(path, headers=r["other"]).status_code == 404
    assert client.get(path, headers=r["owner"]).status_code == 200
