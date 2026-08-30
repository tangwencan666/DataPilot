from io import BytesIO
from pathlib import Path

import openpyxl
from fastapi.testclient import TestClient


def xlsx_bytes() -> bytes:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Sales"
    sheet.append(["product", "amount"])
    sheet.append(["A", 10])
    sheet.append(["B", 20])
    workbook.create_sheet("Other")
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def upload_csv(client: TestClient, filename: str = "sales.csv") -> dict:
    response = client.post("/api/v1/datasets", files={"file": (filename, b"product,amount\nA,10\nB,20\nC,\n", "text/csv")})
    assert response.status_code == 201
    return response.json()


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_csv_upload_persists_safe_filename(client: TestClient, upload_dir: Path) -> None:
    dataset = upload_csv(client, "../../sales.csv")
    assert dataset["original_filename"] == "sales.csv"
    assert dataset["status"] == "READY"
    assert dataset["row_count"] == 3
    assert dataset["stored_filename"] != "sales.csv"
    assert (upload_dir / dataset["stored_filename"]).is_file()


def test_xlsx_upload_uses_first_sheet(client: TestClient) -> None:
    response = client.post(
        "/api/v1/datasets", files={"file": ("book.xlsx", xlsx_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["file_type"] == "xlsx"
    assert body["metadata_json"]["sheet_names"] == ["Sales", "Other"]
    assert body["metadata_json"]["selected_sheet"] == "Sales"


def test_invalid_extension(client: TestClient) -> None:
    response = client.post("/api/v1/datasets", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert response.status_code == 400


def test_file_too_large(client: TestClient) -> None:
    response = client.post("/api/v1/datasets", files={"file": ("large.csv", b"a\n" + b"1" * (1024 * 1024), "text/csv")})
    assert response.status_code == 413


def test_corrupt_csv_and_xlsx(client: TestClient) -> None:
    csv_response = client.post("/api/v1/datasets", files={"file": ("bad.csv", b"\xff\xfe\x00", "text/csv")})
    xlsx_response = client.post(
        "/api/v1/datasets", files={"file": ("bad.xlsx", b"not a zip", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert csv_response.status_code == 422
    assert xlsx_response.status_code == 422


def test_list_and_detail(client: TestClient) -> None:
    created = upload_csv(client)
    listing = client.get("/api/v1/datasets?page=1&page_size=10")
    detail = client.get(f"/api/v1/datasets/{created['id']}")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["id"] == created["id"]
    assert detail.status_code == 200


def test_dataset_not_found(client: TestClient) -> None:
    assert client.get("/api/v1/datasets/missing").status_code == 404
    assert client.get("/api/v1/datasets/missing/preview").status_code == 404


def test_preview_is_limited(client: TestClient) -> None:
    created = upload_csv(client)
    response = client.get(f"/api/v1/datasets/{created['id']}/preview")
    assert response.status_code == 200
    body = response.json()
    assert body["preview_limit"] == 2
    assert len(body["preview_rows"]) == 2
    assert body["columns"][1]["missing"] == 1


def test_delete_removes_database_and_file(client: TestClient, upload_dir: Path) -> None:
    created = upload_csv(client)
    path = upload_dir / created["stored_filename"]
    assert client.delete(f"/api/v1/datasets/{created['id']}").status_code == 204
    assert not path.exists()
    assert client.get(f"/api/v1/datasets/{created['id']}").status_code == 404


def test_delete_succeeds_when_file_is_missing(client: TestClient, upload_dir: Path) -> None:
    created = upload_csv(client)
    (upload_dir / created["stored_filename"]).unlink()
    assert client.delete(f"/api/v1/datasets/{created['id']}").status_code == 204


def test_profile_generation_csv_and_refresh(client: TestClient) -> None:
    created = upload_csv(client)
    first = client.post(f"/api/v1/datasets/{created['id']}/profile")
    fetched = client.get(f"/api/v1/datasets/{created['id']}/profile")
    refreshed = client.post(f"/api/v1/datasets/{created['id']}/profile")
    assert first.status_code == fetched.status_code == refreshed.status_code == 200
    assert first.json()["status"] == "READY"
    assert first.json()["profile"]["summary"]["row_count"] == 3
    assert refreshed.json()["id"] == first.json()["id"]


def test_dataset_delete_cascades_profile(client: TestClient) -> None:
    created = upload_csv(client)
    assert client.post(f"/api/v1/datasets/{created['id']}/profile").status_code == 200
    assert client.delete(f"/api/v1/datasets/{created['id']}").status_code == 204
    assert client.get(f"/api/v1/datasets/{created['id']}/profile").status_code == 404


def test_profile_generation_xlsx(client: TestClient) -> None:
    created = client.post(
        "/api/v1/datasets", files={"file": ("book.xlsx", xlsx_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    ).json()
    response = client.post(f"/api/v1/datasets/{created['id']}/profile")
    assert response.status_code == 200
    assert response.json()["profile"]["summary"]["row_count"] == 2


def test_profile_not_found_and_dataset_not_found(client: TestClient) -> None:
    created = upload_csv(client)
    assert client.get(f"/api/v1/datasets/{created['id']}/profile").status_code == 404
    assert client.post("/api/v1/datasets/missing/profile").status_code == 404


def test_profile_failure_is_persisted(client: TestClient, upload_dir: Path) -> None:
    created = upload_csv(client)
    (upload_dir / created["stored_filename"]).write_bytes(b"\xff\xfe")
    response = client.post(f"/api/v1/datasets/{created['id']}/profile")
    failed = client.get(f"/api/v1/datasets/{created['id']}/profile")
    assert response.status_code == 422
    assert failed.status_code == 200
    assert failed.json()["status"] == "FAILED"
    assert "traceback" not in failed.json()["error_message"].lower()
