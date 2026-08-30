from app.config import Settings


def register(client, email="a@example.com", password="password123"):
    return client.post("/api/v1/auth/register", json={"email": email, "password": password})


def auth(response):
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def upload(client, headers, name="sales.csv"):
    return client.post("/api/v1/datasets", headers=headers, files={"file": (name, b"region,sales\nEast,10\nWest,20\n", "text/csv")})


def test_register_login_and_me(client):
    response = register(client)
    assert response.status_code == 201
    assert response.json()["user"]["email"] == "a@example.com"
    login = client.post("/api/v1/auth/login", json={"email": "A@example.com", "password": "password123"})
    assert login.status_code == 200
    assert client.get("/api/v1/auth/me", headers=auth(login)).json()["email"] == "a@example.com"


def test_duplicate_email_is_rejected(client):
    assert register(client).status_code == 201
    assert register(client, "A@EXAMPLE.COM").status_code == 409


def test_invalid_password_is_rejected(client):
    register(client)
    assert client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "wrong-pass"}).status_code == 401


def test_missing_and_invalid_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_dataset_account_isolation(client):
    a = auth(register(client, "a@example.com"))
    b = auth(register(client, "b@example.com"))
    dataset_id = upload(client, a).json()["id"]
    assert client.get(f"/api/v1/datasets/{dataset_id}", headers=a).status_code == 200
    assert client.get("/api/v1/datasets", headers=b).json()["total"] == 0
    for suffix in ("", "/preview", "/profile", "/queries", "/analyses", "/charts", "/agent-runs", "/reports"):
        assert client.get(f"/api/v1/datasets/{dataset_id}{suffix}", headers=b).status_code == 404
    assert client.delete(f"/api/v1/datasets/{dataset_id}", headers=b).status_code == 404


def test_request_id_and_security_headers(client):
    response = client.get("/api/v1/health", headers={"X-Request-ID": "test-correlation"})
    assert response.headers["X-Request-ID"] == "test-correlation"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_readiness_and_metrics(client):
    assert client.get("/ready").status_code == 200
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "datapilot_http_requests_total" in metrics.text


def test_production_configuration_rejects_weak_defaults():
    try:
        Settings(app_env="production", auth_required=True)
    except ValueError as exc:
        assert "SECRET_KEY" in str(exc)
    else:
        raise AssertionError("weak production settings were accepted")
