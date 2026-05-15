from __future__ import annotations

import os
import queue
import secrets
import shutil
import subprocess
import threading
import time
from pathlib import Path

from .schemas import ApiMessage, CodexAuthStatus, now_iso
from .settings import Settings
from .store import Store


class CodexAuthManager:
    def __init__(self, settings: Settings, store: Store) -> None:
        self.settings = settings
        self.store = store

    def status_for(self, user_id: str) -> CodexAuthStatus:
        return self.store.codex_auth.get(
            user_id,
            CodexAuthStatus(mode="none", state="missing", last_checked_at=now_iso()),
        )

    def start_login(self, user_id: str) -> tuple[str, CodexAuthStatus, ApiMessage]:
        login_id = f"login_{secrets.token_hex(8)}"
        auth_home = self.user_codex_home(user_id)
        auth_home.mkdir(parents=True, exist_ok=True)

        if self.settings.codex_login_mode == "mock":
            status = CodexAuthStatus(
                mode="chatgpt",
                state="failed",
                account_label=None,
                token_fingerprint=None,
                last_checked_at=now_iso(),
                fallback_api_key=self.status_for(user_id).fallback_api_key,
            )
        else:
            status = self._try_real_device_auth(user_id, auth_home, login_id)
        self.store.codex_auth[user_id] = status
        message_key = "codex.login.failed" if status.state == "failed" else "codex.login.started"
        return login_id, status, ApiMessage(code=message_key, message_key=message_key)

    def _try_real_device_auth(self, user_id: str, auth_home: Path, login_id: str) -> CodexAuthStatus:
        if not shutil.which(self.settings.codex_command):
            return CodexAuthStatus(
                mode="chatgpt",
                state="failed",
                last_checked_at=now_iso(),
                fallback_api_key=self.status_for(user_id).fallback_api_key,
            )
        try:
            process = subprocess.Popen(
                [self.settings.codex_command, "login", "--device-auth"],
                cwd=str(auth_home),
                env={**os.environ, "CODEX_HOME": str(auth_home)},
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            lines: queue.Queue[str] = queue.Queue()

            def read_output() -> None:
                if not process.stdout:
                    return
                for output_line in process.stdout:
                    lines.put(output_line)

            threading.Thread(target=read_output, daemon=True).start()
            login_url = None
            deadline = time.time() + 8
            while time.time() < deadline and not login_url:
                try:
                    login_url = _extract_url(lines.get(timeout=0.5))
                except queue.Empty:
                    if process.poll() is not None:
                        break
            if not login_url and process.poll() is None:
                process.terminate()
        except Exception:
            return CodexAuthStatus(
                mode="chatgpt",
                state="failed",
                last_checked_at=now_iso(),
                fallback_api_key=self.status_for(user_id).fallback_api_key,
            )
        return CodexAuthStatus(
            mode="chatgpt",
            state="pending" if login_url else "failed",
            last_checked_at=now_iso(),
            fallback_api_key=self.status_for(user_id).fallback_api_key,
            login_url=login_url,
            user_code=login_id[-6:].upper() if login_url else None,
        )

    def cancel_login(self, user_id: str) -> CodexAuthStatus:
        current = self.status_for(user_id)
        status = current.model_copy(update={"state": "missing", "last_checked_at": now_iso(), "login_url": None, "user_code": None})
        self.store.codex_auth[user_id] = status
        return status

    def logout(self, user_id: str) -> CodexAuthStatus:
        fallback = self.status_for(user_id).fallback_api_key
        status = CodexAuthStatus(mode="none", state="missing", last_checked_at=now_iso(), fallback_api_key=fallback)
        self.store.codex_auth[user_id] = status
        return status

    def save_api_key_fallback(self, user_id: str, fingerprint: str) -> CodexAuthStatus:
        status = CodexAuthStatus(
            mode="api_key",
            state="authenticated",
            account_label="OpenAI API key fallback",
            token_fingerprint=fingerprint,
            last_checked_at=now_iso(),
            fallback_api_key=True,
        )
        self.store.codex_auth[user_id] = status
        return status

    def remove_api_key_fallback(self, user_id: str) -> CodexAuthStatus:
        current = self.status_for(user_id)
        status = current.model_copy(update={"fallback_api_key": False, "last_checked_at": now_iso()})
        if status.mode == "api_key":
            status = CodexAuthStatus(mode="none", state="missing", last_checked_at=now_iso(), fallback_api_key=False)
        self.store.codex_auth[user_id] = status
        return status

    def user_codex_home(self, user_id: str) -> Path:
        return self.settings.runtime_dir / "codex-home" / user_id


def _extract_url(text: str) -> str | None:
    for token in text.split():
        if token.startswith("http://") or token.startswith("https://"):
            return token
    return None
