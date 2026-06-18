from __future__ import annotations

from io import BytesIO
import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_auth_and_case_create(client: TestClient):
    email = f"user_{uuid4().hex[:8]}@example.com"
    password = "StrongPass123"
    register = client.post("/api/auth/register", json={"email": email, "password": password})
    assert register.status_code == 200
    token = register.json()["access_token"]

    login = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    token = login.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    create_case = client.post("/api/cases", json={"title": "Test Case"}, headers=headers)
    assert create_case.status_code == 200
    payload = create_case.json()
    assert payload["title"] == "Test Case"


def test_upload_and_run_bicubic_pipeline(client: TestClient):
    email = f"user_{uuid4().hex[:8]}@example.com"
    password = "StrongPass123"
    register = client.post("/api/auth/register", json={"email": email, "password": password})
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_case = client.post("/api/cases", json={"title": "Pipeline Case"}, headers=headers)
    assert create_case.status_code == 200
    case_id = create_case.json()["id"]

    image = Image.new("RGB", (64, 64), color=(120, 120, 120))
    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")
    image_bytes.seek(0)
    upload = client.post(
        f"/api/cases/{case_id}/images",
        headers=headers,
        files={"file": ("sample.png", image_bytes.getvalue(), "image/png")},
    )
    assert upload.status_code == 200
    image_id = upload.json()["id"]

    run_create = client.post(
        "/api/runs",
        headers=headers,
        json={
            "case_id": case_id,
            "image_id": image_id,
            "models": ["bicubic"],
            "scale": 2,
            "reference_image_id": image_id,
        },
    )
    assert run_create.status_code == 200
    run_id = run_create.json()["id"]

    status_payload = {}
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        status = client.get(f"/api/runs/{run_id}", headers=headers)
        assert status.status_code == 200
        status_payload = status.json()
        if status_payload["status"] in {"completed", "failed"}:
            break
        time.sleep(0.1)

    assert status_payload["status"] == "completed", status_payload.get("error_message")
    results = client.get(f"/api/runs/{run_id}/results", headers=headers)
    assert results.status_code == 200
    body = results.json()
    assert len(body["outputs"]) == 1
    assert body["outputs"][0]["model_name"] == "bicubic"
    assert len(body["metrics"]) == 1
    assert body["metrics"][0]["psnr"] is not None

    output_path = body["outputs"][0]["output_path"]
    file_resp = client.get(f"/api/files?path={output_path}&token={token}")
    assert file_resp.status_code == 200
