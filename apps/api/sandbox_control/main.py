from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .codex_auth import CodexAuthManager
from .crypto import SecretBox
from .i18n import CATALOGS, get_catalog
from .preflight import component_health, run_preflight
from .schemas import (
    ApiKeyRequest,
    ApiMessage,
    CodexLoginStartResponse,
    CodexRunCreateRequest,
    DashboardSnapshot,
    LoginRequest,
    LoginResponse,
    RunStatus,
    SandboxCreateRequest,
    SecretRequest,
    User,
)
from .settings import settings
from .store import Store

app = FastAPI(title="Sandbox Control", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = Store(SecretBox(settings.secret_key))
store.seed(settings.admin_password)
codex_auth = CodexAuthManager(settings, store)


def current_user(authorization: Annotated[str | None, Header()] = None) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": "auth.required", "message_key": "auth.required"})
    token = authorization.removeprefix("Bearer ").strip()
    user = store.user_for_token(token)
    if not user:
        raise HTTPException(status_code=401, detail={"code": "auth.required", "message_key": "auth.required"})
    return user


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}


@app.post("/api/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    result = store.authenticate(payload.username, payload.password)
    if not result:
        raise HTTPException(
            status_code=401,
            detail={"code": "auth.invalid_credentials", "message_key": "auth.invalid_credentials"},
        )
    token, user = result
    return LoginResponse(token=token, user=user)


@app.get("/api/auth/me", response_model=User)
def me(user: User = Depends(current_user)) -> User:
    return user


@app.get("/api/i18n/catalog")
def catalog(locale: str = "zh-CN") -> dict[str, object]:
    return {"locale": locale if locale in CATALOGS else "zh-CN", "version": "0.1.0", "messages": get_catalog(locale)}


@app.get("/api/dashboard", response_model=DashboardSnapshot)
def dashboard(user: User = Depends(current_user)) -> DashboardSnapshot:
    runs = list(store.runs.values())
    selected = runs[0]
    return DashboardSnapshot(
        user=user,
        preflight=run_preflight(),
        components=component_health(),
        sandboxes=list(store.sandboxes.values()),
        runs=runs,
        selected_run=selected,
        events=store.events.get(selected.id, []),
        audit=store.audit[:20],
        codex_auth=codex_auth.status_for(user.id),
        quota={"sandboxes": 87, "sandbox_limit": 150, "cpu": 48, "cpu_limit": 80, "ram": 196, "ram_limit": 320, "cost": 142.37},
    )


@app.get("/api/codex-auth/status")
def codex_status(user: User = Depends(current_user)):
    return codex_auth.status_for(user.id)


@app.post("/api/codex-auth/login/start", response_model=CodexLoginStartResponse)
def codex_login_start(user: User = Depends(current_user)) -> CodexLoginStartResponse:
    login_id, status, message = codex_auth.start_login(user.id)
    store.add_audit(user, "CODEX_LOGIN_STARTED", user.id, {"login_id": login_id})
    return CodexLoginStartResponse(login_id=login_id, status=status, message=message)


@app.post("/api/codex-auth/login/cancel")
def codex_login_cancel(user: User = Depends(current_user)) -> dict[str, object]:
    status = codex_auth.cancel_login(user.id)
    store.add_audit(user, "CODEX_LOGIN_CANCELLED", user.id, {})
    return {"status": status, "message": ApiMessage(code="codex.login.cancelled", message_key="codex.login.cancelled")}


@app.post("/api/codex-auth/logout")
def codex_logout(user: User = Depends(current_user)) -> dict[str, object]:
    status = codex_auth.logout(user.id)
    store.add_audit(user, "CODEX_LOGGED_OUT", user.id, {})
    return {"status": status, "message": ApiMessage(code="codex.login.logged_out", message_key="codex.login.logged_out")}


@app.post("/api/codex-auth/api-key")
def codex_api_key(payload: ApiKeyRequest, user: User = Depends(current_user)) -> dict[str, object]:
    if payload.api_key:
        summary = store.save_secret(user, "openai_api_key", "OpenAI API key fallback", payload.api_key)
        status = codex_auth.save_api_key_fallback(user.id, summary.fingerprint)
        return {"status": status, "message": ApiMessage(code="codex.api_key.saved", message_key="codex.api_key.saved")}
    status = codex_auth.remove_api_key_fallback(user.id)
    return {"status": status, "message": ApiMessage(code="codex.api_key.removed", message_key="codex.api_key.removed")}


@app.get("/api/infra/preflight")
def preflight() -> dict[str, object]:
    return {"preflight": run_preflight(), "message": ApiMessage(code="infra.preflight.ready", message_key="infra.preflight.ready")}


@app.get("/api/infra/components")
def components():
    return {"components": component_health()}


@app.get("/api/sandboxes")
def sandboxes(user: User = Depends(current_user)):
    return {"sandboxes": list(store.sandboxes.values())}


@app.post("/api/sandboxes")
def create_sandbox(payload: SandboxCreateRequest, user: User = Depends(current_user)):
    sandbox = store.create_sandbox(user, payload.template, payload.workspace)
    return {"sandbox": sandbox, "message": ApiMessage(code="sandbox.created", message_key="sandbox.created")}


@app.post("/api/sandboxes/{sandbox_id}/{action}")
def sandbox_action(sandbox_id: str, action: str, user: User = Depends(current_user)):
    sandbox = store.sandboxes[sandbox_id]
    mapping = {
        "pause": ("paused", "sandbox.paused"),
        "resume": ("running", "sandbox.resumed"),
        "kill": ("killed", "sandbox.killed"),
    }
    if action not in mapping:
        raise HTTPException(status_code=400, detail={"code": "sandbox.action_invalid", "message_key": "sandbox.action_invalid"})
    status, message_key = mapping[action]
    updated = sandbox.model_copy(update={"status": status})
    store.sandboxes[sandbox_id] = updated
    store.add_audit(user, f"SANDBOX_{action.upper()}", sandbox_id, {})
    return {"sandbox": updated, "message": ApiMessage(code=message_key, message_key=message_key)}


@app.get("/api/codex-runs")
def codex_runs(user: User = Depends(current_user)):
    return {"runs": list(store.runs.values())}


@app.post("/api/codex-runs")
def create_codex_run(payload: CodexRunCreateRequest, user: User = Depends(current_user)):
    run = store.create_run(user, payload.repo, payload.branch, payload.prompt, payload.template)
    return {"run": run, "message": ApiMessage(code="run.created", message_key="run.created")}


@app.get("/api/codex-runs/{run_id}")
def codex_run(run_id: str, user: User = Depends(current_user)):
    return {"run": store.runs[run_id], "events": store.events.get(run_id, [])}


@app.post("/api/codex-runs/{run_id}/{action}")
def codex_run_action(run_id: str, action: str, user: User = Depends(current_user)):
    mapping = {
        "approve": (RunStatus.approved, "RUN_APPROVED", "run.approved"),
        "reject": (RunStatus.rejected, "RUN_REJECTED", "run.rejected"),
        "pause": (RunStatus.paused, "RUN_PAUSED", "run.paused"),
        "kill": (RunStatus.killed, "RUN_KILLED", "run.killed"),
    }
    if action not in mapping:
        raise HTTPException(status_code=400, detail={"code": "run.action_invalid", "message_key": "run.action_invalid"})
    status, audit_code, message_key = mapping[action]
    run = store.update_run_status(user, run_id, status, audit_code)
    return {"run": run, "message": ApiMessage(code=message_key, message_key=message_key)}


@app.get("/api/codex-runs/{run_id}/events")
async def codex_run_events(run_id: str, user: User = Depends(current_user)):
    async def event_stream():
        sent = 0
        while sent < 4:
            events = store.events.get(run_id, [])
            for event in events[sent:]:
                yield f"event: codex-event\ndata: {event.model_dump_json()}\n\n"
                sent += 1
            await asyncio.sleep(0.5)
        yield f"event: heartbeat\ndata: {json.dumps({'run_id': run_id})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/secrets")
def list_secrets(user: User = Depends(current_user)):
    return {"secrets": store.list_secrets(user)}


@app.post("/api/secrets")
def save_secret(payload: SecretRequest, user: User = Depends(current_user)):
    summary = store.save_secret(user, payload.kind, payload.label, payload.value)
    return {"secret": summary, "message": ApiMessage(code="secret.saved", message_key="secret.saved")}


@app.delete("/api/secrets/{secret_id}")
def delete_secret(secret_id: str, user: User = Depends(current_user)):
    deleted = store.delete_secret(user, secret_id)
    if not deleted:
        raise HTTPException(status_code=404, detail={"code": "secret.not_found", "message_key": "secret.not_found"})
    return {"ok": True, "message": ApiMessage(code="secret.removed", message_key="secret.removed")}


@app.get("/api/audit")
def audit(user: User = Depends(current_user)):
    return {"audit": store.audit}


if settings.frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=settings.frontend_dist / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        index_path = settings.frontend_dist / "index.html"
        target = settings.frontend_dist / full_path
        if target.exists() and target.is_file():
            return FileResponse(target)
        return FileResponse(index_path)
