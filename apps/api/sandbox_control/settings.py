from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    env: str
    host: str
    port: int
    secret_key: str
    admin_password: str
    codex_login_mode: str
    codex_command: str
    frontend_dist: Path
    runtime_dir: Path

    @classmethod
    def from_env(cls) -> "Settings":
        root = Path(__file__).resolve().parents[3]
        return cls(
            env=os.getenv("SANDBOX_CONTROL_ENV", "development"),
            host=os.getenv("SANDBOX_CONTROL_API_HOST", "0.0.0.0"),
            port=int(os.getenv("SANDBOX_CONTROL_API_PORT", "8080")),
            secret_key=os.getenv("SANDBOX_CONTROL_SECRET_KEY", "dev-only-secret-key"),
            admin_password=os.getenv("SANDBOX_CONTROL_ADMIN_PASSWORD", "sandbox-control-admin"),
            codex_login_mode=os.getenv("SANDBOX_CONTROL_CODEX_LOGIN_MODE", "real"),
            codex_command=os.getenv("SANDBOX_CONTROL_CODEX_COMMAND", "codex"),
            frontend_dist=root / os.getenv("SANDBOX_CONTROL_FRONTEND_DIST", "apps/web/dist"),
            runtime_dir=root / "apps/api/.runtime",
        )


settings = Settings.from_env()
