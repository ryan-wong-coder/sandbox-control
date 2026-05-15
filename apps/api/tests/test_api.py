from __future__ import annotations

import os

from fastapi.testclient import TestClient

os.environ.setdefault("SANDBOX_CONTROL_CODEX_LOGIN_MODE", "mock")

from sandbox_control.main import app


client = TestClient(app)


def login() -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "sandbox-control-admin"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_login_and_dashboard() -> None:
    headers = login()
    response = client.get("/api/dashboard", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["username"] == "admin"
    assert data["selected_run"] is None
    assert data["runs"] == []
    assert data["codex_auth"]["state"] in {"missing", "pending", "authenticated"}


def test_i18n_catalogs_have_matching_keys() -> None:
    zh = client.get("/api/i18n/catalog?locale=zh-CN").json()["messages"]
    en = client.get("/api/i18n/catalog?locale=en-US").json()["messages"]
    assert set(zh.keys()) == set(en.keys())
    assert "codex.login.started" in zh


def test_codex_login_and_api_key_fallback() -> None:
    headers = login()
    start = client.post("/api/codex-auth/login/start", headers=headers)
    assert start.status_code == 200
    assert start.json()["status"]["mode"] == "chatgpt"
    fallback = client.post("/api/codex-auth/api-key", headers=headers, json={"api_key": "sk-test"})
    assert fallback.status_code == 200
    assert fallback.json()["status"]["fallback_api_key"] is True


def test_create_run_and_approve() -> None:
    headers = login()
    created = client.post(
        "/api/codex-runs",
        headers=headers,
        json={"repo": "", "branch": "main", "prompt": "Run tests", "template": "python-3.11"},
    )
    assert created.status_code == 200
    run_id = created.json()["run"]["id"]
    approved = client.post(f"/api/codex-runs/{run_id}/approve", headers=headers)
    assert approved.status_code == 200
    assert approved.json()["run"]["status"] == "approved"


def test_secret_summary_does_not_leak_value() -> None:
    headers = login()
    response = client.post(
        "/api/secrets",
        headers=headers,
        json={"kind": "git_pat", "label": "GitHub", "value": "ghp_secret"},
    )
    assert response.status_code == 200
    payload = response.json()["secret"]
    assert "ghp_secret" not in str(payload)
    assert payload["fingerprint"]
