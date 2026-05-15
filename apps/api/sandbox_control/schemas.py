from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Role(StrEnum):
    admin = "admin"
    operator = "operator"
    viewer = "viewer"


class RunStatus(StrEnum):
    queued = "queued"
    provisioning = "provisioning"
    cloning = "cloning"
    planning = "planning"
    executing = "executing"
    review = "review"
    approved = "approved"
    rejected = "rejected"
    paused = "paused"
    failed = "failed"
    completed = "completed"
    killed = "killed"


class SandboxStatus(StrEnum):
    running = "running"
    paused = "paused"
    failed = "failed"
    killed = "killed"


class ApiMessage(BaseModel):
    code: str
    message_key: str
    params: dict[str, Any] = Field(default_factory=dict)


class User(BaseModel):
    id: str
    username: str
    display_name: str
    role: Role
    locale: str = "zh-CN"


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: User


class MetricPoint(BaseModel):
    label: str
    value: float


class InfraCheck(BaseModel):
    id: str
    label: str
    status: Literal["pass", "warn", "fail"]
    summary: str
    detail: str


class InfraPreflight(BaseModel):
    checked_at: str
    overall_status: Literal["pass", "warn", "fail"]
    overall_score: int
    checks: list[InfraCheck]


class ComponentHealth(BaseModel):
    id: str
    label: str
    status: Literal["healthy", "warn", "failed"]
    version: str
    summary: str
    sparkline: list[float]


class Sandbox(BaseModel):
    id: str
    template: str
    owner_id: str
    status: SandboxStatus
    created_at: str
    workspace: str
    host: str | None = None
    resources: dict[str, float] = Field(default_factory=dict)


class SandboxCreateRequest(BaseModel):
    template: str = "python-3.11-codex"
    workspace: str = "/workspace"


class CodexAuthStatus(BaseModel):
    mode: Literal["chatgpt", "api_key", "none"]
    state: Literal["authenticated", "pending", "missing", "failed"]
    account_label: str | None = None
    token_fingerprint: str | None = None
    last_checked_at: str
    fallback_api_key: bool = False
    login_url: str | None = None
    user_code: str | None = None


class CodexLoginStartResponse(BaseModel):
    login_id: str
    status: CodexAuthStatus
    message: ApiMessage


class ApiKeyRequest(BaseModel):
    api_key: str | None = None


class SecretRequest(BaseModel):
    kind: Literal["git_pat", "openai_api_key", "codex_token", "generic"]
    label: str
    value: str


class SecretSummary(BaseModel):
    id: str
    owner_id: str
    kind: str
    label: str
    fingerprint: str
    created_at: str
    updated_at: str


class CodexRunCreateRequest(BaseModel):
    repo: str = ""
    branch: str = "main"
    prompt: str = ""
    template: str = "python-3.11"


class WorkflowStep(BaseModel):
    id: str
    label: str
    status: Literal["complete", "active", "pending", "failed"]
    at: str | None = None


class CodexRun(BaseModel):
    id: str
    repo: str
    branch: str
    prompt: str
    sandbox_id: str
    template: str
    owner_id: str
    owner_name: str
    status: RunStatus
    created_at: str
    elapsed_seconds: int
    step: str
    progress: int
    resources: dict[str, float]
    workflow: list[WorkflowStep]
    diff_summary: dict[str, Any]
    approval_required: bool = True


class RunEvent(BaseModel):
    id: str
    run_id: str
    at: str
    level: Literal["info", "warn", "error", "pass"]
    event_type: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)


class AuditEvent(BaseModel):
    id: str
    at: str
    actor_id: str
    actor_name: str
    event_code: str
    resource: str
    params: dict[str, Any] = Field(default_factory=dict)


class DashboardSnapshot(BaseModel):
    user: User
    preflight: InfraPreflight
    components: list[ComponentHealth]
    sandboxes: list[Sandbox]
    runs: list[CodexRun]
    selected_run: CodexRun | None
    events: list[RunEvent]
    audit: list[AuditEvent]
    codex_auth: CodexAuthStatus
    quota: dict[str, float]
