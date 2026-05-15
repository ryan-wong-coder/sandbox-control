from __future__ import annotations

CATALOGS: dict[str, dict[str, str]] = {
    "zh-CN": {
        "app.name": "Sandbox Control",
        "auth.invalid_credentials": "用户名或密码错误",
        "auth.required": "需要登录",
        "codex.login.started": "Codex 登录已启动",
        "codex.login.failed": "Codex 登录启动失败",
        "codex.login.cancelled": "Codex 登录已取消",
        "codex.login.logged_out": "Codex 已退出登录",
        "codex.api_key.saved": "API Key 备用登录已保存",
        "codex.api_key.removed": "API Key 备用登录已移除",
        "infra.preflight.ready": "单机预检已完成",
        "run.created": "Codex run 已创建",
        "run.approved": "运行已批准",
        "run.rejected": "运行已拒绝",
        "run.paused": "运行已暂停",
        "run.killed": "运行已终止",
        "sandbox.created": "Sandbox 已创建",
        "sandbox.paused": "Sandbox 已暂停",
        "sandbox.resumed": "Sandbox 已恢复",
        "sandbox.killed": "Sandbox 已销毁",
        "secret.saved": "密钥已保存",
        "secret.removed": "密钥已移除",
    },
    "en-US": {
        "app.name": "Sandbox Control",
        "auth.invalid_credentials": "Invalid username or password",
        "auth.required": "Authentication required",
        "codex.login.started": "Codex login started",
        "codex.login.failed": "Codex login failed to start",
        "codex.login.cancelled": "Codex login cancelled",
        "codex.login.logged_out": "Codex logged out",
        "codex.api_key.saved": "API key fallback saved",
        "codex.api_key.removed": "API key fallback removed",
        "infra.preflight.ready": "Single-node preflight completed",
        "run.created": "Codex run created",
        "run.approved": "Run approved",
        "run.rejected": "Run rejected",
        "run.paused": "Run paused",
        "run.killed": "Run killed",
        "sandbox.created": "Sandbox created",
        "sandbox.paused": "Sandbox paused",
        "sandbox.resumed": "Sandbox resumed",
        "sandbox.killed": "Sandbox destroyed",
        "secret.saved": "Secret saved",
        "secret.removed": "Secret removed",
    },
}


def get_catalog(locale: str) -> dict[str, str]:
    return CATALOGS.get(locale, CATALOGS["zh-CN"])
