from __future__ import annotations

from dataclasses import dataclass, field
import itertools
import secrets
from typing import Any

from .crypto import SecretBox
from .schemas import (
    AuditEvent,
    CodexAuthStatus,
    CodexRun,
    Role,
    RunEvent,
    RunStatus,
    Sandbox,
    SandboxStatus,
    SecretSummary,
    User,
    WorkflowStep,
    now_iso,
)
from .security import hash_password, new_token, verify_password


@dataclass
class SecretRecord:
    summary: SecretSummary
    encrypted_value: str


@dataclass
class UserRecord:
    user: User
    password_hash: str


@dataclass
class Store:
    secret_box: SecretBox
    users: dict[str, UserRecord] = field(default_factory=dict)
    sessions: dict[str, str] = field(default_factory=dict)
    sandboxes: dict[str, Sandbox] = field(default_factory=dict)
    runs: dict[str, CodexRun] = field(default_factory=dict)
    events: dict[str, list[RunEvent]] = field(default_factory=dict)
    audit: list[AuditEvent] = field(default_factory=list)
    secrets: dict[str, SecretRecord] = field(default_factory=dict)
    codex_auth: dict[str, CodexAuthStatus] = field(default_factory=dict)
    _counter: itertools.count = field(default_factory=lambda: itertools.count(1))

    def seed(self, admin_password: str) -> None:
        if self.users:
            return
        admin = User(id="usr_admin", username="admin", display_name="Admin", role=Role.admin)
        self.users[admin.username] = UserRecord(admin, hash_password(admin_password))
        operator = User(id="usr_agent", username="operator", display_name="Operator", role=Role.operator)
        self.users[operator.username] = UserRecord(operator, hash_password("operator"))
        self.codex_auth[admin.id] = CodexAuthStatus(
            mode="none",
            state="missing",
            last_checked_at=now_iso(),
            fallback_api_key=False,
        )
        self.codex_auth[operator.id] = CodexAuthStatus(
            mode="none",
            state="missing",
            last_checked_at=now_iso(),
            fallback_api_key=False,
        )

    def _build_run(
        self,
        owner: User,
        run_id: str,
        sandbox_id: str,
        repo: str,
        branch: str,
        prompt: str,
        status: RunStatus,
        progress: int,
    ) -> CodexRun:
        active_index_by_status = {
            RunStatus.queued: 0,
            RunStatus.provisioning: 1,
            RunStatus.cloning: 2,
            RunStatus.planning: 3,
            RunStatus.executing: 4,
            RunStatus.review: 5,
            RunStatus.completed: 6,
            RunStatus.failed: 6,
            RunStatus.killed: 6,
            RunStatus.approved: 6,
            RunStatus.rejected: 6,
            RunStatus.paused: 4,
        }
        active_index = active_index_by_status.get(status, 0)
        step_names = ["Queued", "Provision", "Clone Repo", "Init Env", "Plan", "Execute", "Review", "Complete"]
        workflow = [
            WorkflowStep(
                id=name.lower().replace(" ", "_"),
                label=name,
                status="failed" if status == RunStatus.failed and index == active_index else "complete" if index < active_index else "active" if index == active_index else "pending",
                at=now_iso() if index <= active_index else None,
            )
            for index, name in enumerate(step_names)
        ]
        return CodexRun(
            id=run_id,
            repo=repo,
            branch=branch,
            prompt=prompt,
            sandbox_id=sandbox_id,
            template="python-3.11",
            owner_id=owner.id,
            owner_name=owner.display_name,
            status=status,
            created_at=now_iso(),
            elapsed_seconds=0,
            step=status.value,
            progress=progress,
            resources={"cpu": 0, "memory": 0, "disk": 0, "network": 0},
            workflow=workflow,
            diff_summary={"file": "", "added": 0, "removed": 0, "files_changed": 0, "hunks": []},
            approval_required=False,
        )

    def authenticate(self, username: str, password: str) -> tuple[str, User] | None:
        record = self.users.get(username)
        if not record or not verify_password(password, record.password_hash):
            return None
        token = new_token("sct")
        self.sessions[token] = record.user.id
        return token, record.user

    def user_for_token(self, token: str) -> User | None:
        user_id = self.sessions.get(token)
        if not user_id:
            return None
        for record in self.users.values():
            if record.user.id == user_id:
                return record.user
        return None

    def create_sandbox(self, owner: User, template: str, workspace: str) -> Sandbox:
        sandbox = Sandbox(
            id=f"sbx-{secrets.token_hex(4)}",
            template=template,
            owner_id=owner.id,
            status=SandboxStatus.running,
            created_at=now_iso(),
            workspace=workspace,
            host="local-worker",
            resources={"cpu": 0, "memory": 0, "disk": 0, "network": 0},
        )
        self.sandboxes[sandbox.id] = sandbox
        self.add_audit(owner, "SANDBOX_CREATED", sandbox.id, {"template": template})
        return sandbox

    def create_run(self, owner: User, repo: str, branch: str, prompt: str, template: str) -> CodexRun:
        sandbox = self.create_sandbox(owner, template=template, workspace="/workspace")
        run_id = f"run-{secrets.token_hex(4)}"
        run = self._build_run(owner, run_id, sandbox.id, repo, branch, prompt, RunStatus.queued, 5)
        self.runs[run.id] = run
        self.events[run.id] = [
            RunEvent(id=f"evt_{run.id}_1", run_id=run.id, at=now_iso(), level="info", event_type="run.created", message="queued codex run", payload={"repo": repo, "branch": branch})
        ]
        self.add_audit(owner, "CODEX_RUN_CREATED", run.id, {"repo": repo, "branch": branch})
        return run

    def set_run_status(
        self,
        run_id: str,
        status: RunStatus,
        *,
        progress: int | None = None,
        step: str | None = None,
        diff_summary: dict[str, Any] | None = None,
    ) -> CodexRun:
        run = self.runs[run_id]
        update: dict[str, Any] = {"status": status}
        if progress is not None:
            update["progress"] = progress
        if step is not None:
            update["step"] = step
        if diff_summary is not None:
            update["diff_summary"] = diff_summary
        updated = run.model_copy(update=update)
        updated = self._build_run(
            owner=User(id=updated.owner_id, username="", display_name=updated.owner_name, role=Role.operator),
            run_id=updated.id,
            sandbox_id=updated.sandbox_id,
            repo=updated.repo,
            branch=updated.branch,
            prompt=updated.prompt,
            status=status,
            progress=updated.progress,
        ).model_copy(update={
            "created_at": updated.created_at,
            "elapsed_seconds": updated.elapsed_seconds,
            "step": update.get("step", updated.step),
            "diff_summary": update.get("diff_summary", updated.diff_summary),
            "approval_required": updated.approval_required,
        })
        self.runs[run_id] = updated
        return updated

    def append_event(
        self,
        run_id: str,
        level: str,
        event_type: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> RunEvent:
        event = RunEvent(
            id=f"evt_{run_id}_{len(self.events.get(run_id, [])) + 1}",
            run_id=run_id,
            at=now_iso(),
            level=level,  # type: ignore[arg-type]
            event_type=event_type,
            message=message,
            payload=payload or {},
        )
        self.events.setdefault(run_id, []).append(event)
        return event

    def latest_secret_value(self, owner_id: str, kind: str) -> str | None:
        matching = [
            record
            for record in self.secrets.values()
            if record.summary.owner_id == owner_id and record.summary.kind == kind
        ]
        if not matching:
            return None
        matching.sort(key=lambda record: record.summary.updated_at, reverse=True)
        return self.secret_box.decrypt(matching[0].encrypted_value)

    def update_run_status(self, user: User, run_id: str, status: RunStatus, code: str) -> CodexRun:
        run = self.runs[run_id]
        updated = run.model_copy(update={"status": status})
        self.runs[run_id] = updated
        event = RunEvent(
            id=f"evt_{run_id}_{len(self.events.get(run_id, [])) + 1}",
            run_id=run_id,
            at=now_iso(),
            level="warn" if status in {RunStatus.rejected, RunStatus.killed} else "info",
            event_type=code.lower(),
            message=code,
        )
        self.events.setdefault(run_id, []).append(event)
        self.add_audit(user, code, run_id, {})
        return updated

    def add_audit(self, actor: User, event_code: str, resource: str, params: dict[str, Any]) -> None:
        self.audit.insert(
            0,
            AuditEvent(
                id=f"aud_{secrets.token_hex(6)}",
                at=now_iso(),
                actor_id=actor.id,
                actor_name=actor.display_name,
                event_code=event_code,
                resource=resource,
                params=params,
            ),
        )

    def save_secret(self, owner: User, kind: str, label: str, value: str) -> SecretSummary:
        secret_id = f"sec_{secrets.token_hex(6)}"
        summary = SecretSummary(
            id=secret_id,
            owner_id=owner.id,
            kind=kind,
            label=label,
            fingerprint=self.secret_box.fingerprint(value),
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        self.secrets[secret_id] = SecretRecord(summary, self.secret_box.encrypt(value))
        self.add_audit(owner, "SECRET_SAVED", secret_id, {"kind": kind})
        return summary

    def list_secrets(self, owner: User) -> list[SecretSummary]:
        return [record.summary for record in self.secrets.values() if record.summary.owner_id == owner.id]

    def delete_secret(self, owner: User, secret_id: str) -> bool:
        record = self.secrets.get(secret_id)
        if not record or record.summary.owner_id != owner.id:
            return False
        del self.secrets[secret_id]
        self.add_audit(owner, "SECRET_REMOVED", secret_id, {})
        return True
