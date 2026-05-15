# AGENTS.md

## Project Contract

Sandbox Control is a Python/FastAPI + React/Vite internal platform for managing experimental single-node E2B-style sandbox infrastructure and remote Codex sessions.

## Engineering Rules

- Keep `README.md` and `README.zh-CN.md` structurally aligned.
- Keep this file as the English source of truth and mirror user-facing guidance in `docs/AGENTS.zh-CN.md`.
- Never commit secrets, passwords, API keys, Git PATs, Codex `auth.json`, runtime state, or real `.env` files.
- Do not claim Firecracker/E2B runtime success unless preflight checks and runtime smoke tests prove it.
- Preserve bilingual i18n for all visible product text, status labels, errors, and audit event names.
- Treat single-node E2B as experimental. The control plane may run even when Firecracker is blocked, but the UI must surface the blocker.

## Validation

- Backend: `uv run pytest`.
- Frontend: `npm test` and `npm run build` in `apps/web`.
- Product smoke: login, switch language, start Codex login, create run, approve run, open Conversations page, inspect Infra preflight.
