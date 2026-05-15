from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
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
        admin = User(id="usr_admin", username="admin", display_name="Sarah Kim", role=Role.admin)
        self.users[admin.username] = UserRecord(admin, hash_password(admin_password))
        operator = User(id="usr_agent", username="operator", display_name="Codex Agent", role=Role.operator)
        self.users[operator.username] = UserRecord(operator, hash_password("operator"))
        self.codex_auth[admin.id] = CodexAuthStatus(
            mode="none",
            state="missing",
            last_checked_at=now_iso(),
            fallback_api_key=False,
        )
        self._seed_dashboard(admin)

    def _seed_dashboard(self, admin: User) -> None:
        sandbox = Sandbox(
            id="sbx-1a3f9b7d",
            template="python-3.11",
            owner_id=admin.id,
            status=SandboxStatus.running,
            created_at=now_iso(),
            workspace="/workspace",
            host="10.0.0.12",
            resources={"cpu": 60, "memory": 53, "disk": 44, "network": 24},
        )
        self.sandboxes[sandbox.id] = sandbox
        run = self._build_run(
            owner=admin,
            run_id="run-8f3a1c2e",
            sandbox_id=sandbox.id,
            repo="acme/web-app",
            branch="feat/ai-refactor",
            prompt="Apply a safe patch to the AI runner.",
            status=RunStatus.executing,
            progress=68,
        )
        self.runs[run.id] = run
        self.events[run.id] = [
            RunEvent(id="evt_1", run_id=run.id, at="14:22:10", level="info", event_type="step.started", message='{"step":12,"name":"apply_patch"}'),
            RunEvent(id="evt_2", run_id=run.id, at="14:22:11", level="info", event_type="read", message="reading file src/services/ai/runner.py"),
            RunEvent(id="evt_3", run_id=run.id, at="14:22:13", level="info", event_type="patch", message="patch generated (+24 -8)"),
            RunEvent(id="evt_4", run_id=run.id, at="14:22:19", level="pass", event_type="test", message="pytest -k runner: 6 passed in 3.21s"),
            RunEvent(id="evt_5", run_id=run.id, at="14:22:19", level="info", event_type="step.completed", message='{"status":"success"}'),
        ]
        self.audit.extend(
            [
                AuditEvent(id="aud_1", at="14:22:19", actor_id=admin.id, actor_name=admin.display_name, event_code="STEP_COMPLETED", resource=f"{run.id}/step-12", params={"result": "+24 -8"}),
                AuditEvent(id="aud_2", at="14:22:16", actor_id="usr_agent", actor_name="codex-agent", event_code="TEST_PASSED", resource=run.id, params={"suite": "runner", "passed": 6}),
                AuditEvent(id="aud_3", at="14:20:02", actor_id="system", actor_name="min.system", event_code="SANDBOX_STARTED", resource=sandbox.id, params={"template": sandbox.template}),
            ]
        )
        for idx, status in enumerate([RunStatus.executing, RunStatus.queued, RunStatus.paused, RunStatus.executing, RunStatus.completed], start=2):
            next_run = self._build_run(
                owner=admin,
                run_id=f"run-{secrets.token_hex(4)}",
                sandbox_id=sandbox.id,
                repo=["acme/api-gateway", "acme/worker", "acme/infra"][idx % 3],
                branch=["main", "feat/auth", "fix/schema"][idx % 3],
                prompt="",
                status=status,
                progress=20 + idx * 9,
            )
            self.runs[next_run.id] = next_run
            self.events[next_run.id] = []

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
        active_index = 4 if status in {RunStatus.executing, RunStatus.review} else 1
        step_names = ["Queued", "Provision", "Clone Repo", "Init Env", "Plan", "Execute", "Review", "Complete"]
        workflow = [
            WorkflowStep(
                id=name.lower().replace(" ", "_"),
                label=name,
                status="complete" if index < active_index else "active" if index == active_index else "pending",
                at=f"14:{index:02d}:0{index}" if index <= active_index else None,
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
            elapsed_seconds=18 * 60 + 42,
            step="Step 12/28",
            progress=progress,
            resources={"cpu": 60, "memory": 53, "disk": 44, "network": 24},
            workflow=workflow,
            diff_summary={
                "file": "src/services/ai/runner.py",
                "added": 24,
                "removed": 8,
                "files_changed": 23,
                "hunks": [
                    {"line": 50, "kind": "remove", "text": "response = self.call_model(prompt)"},
                    {"line": 52, "kind": "add", "text": "try:"},
                    {"line": 53, "kind": "add", "text": "    response = self._call_model(prompt)"},
                    {"line": 54, "kind": "add", "text": "    return self._parse(response)"},
                ],
            },
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
            host=f"10.0.0.{20 + next(self._counter)}",
            resources={"cpu": 5, "memory": 12, "disk": 2, "network": 0},
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
