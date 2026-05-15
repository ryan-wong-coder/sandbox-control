# Sandbox Control

Sandbox Control is an internal, multi-user control plane for experimental self-hosted E2B-style sandboxes and remote Codex sessions. It combines a FastAPI backend with a React/Vite dashboard, bilingual UI, per-user Codex login state, sandbox lifecycle controls, Codex run review, logs, diffs, audit events, and a dedicated conversation page.

![Dashboard concept](docs/assets/concept-dashboard.png)

## Implemented Capabilities

- Local account login with `admin`, `operator`, and `viewer` roles.
- Per-user encrypted secret summaries for Git PATs, Codex/ChatGPT tokens, and API-key fallback.
- Codex auth endpoints for per-user ChatGPT login flow, cancellation, logout, and OpenAI API-key fallback.
- Codex run queue, selected run detail, workflow timeline, approval controls, logs, diff summary, and audit events.
- A dedicated Codex conversation page with messages, tool approval cards, terminal stream, and file/diff rail.
- Single-node infrastructure preflight for Linux, CPU virtualization, `/dev/kvm`, Firecracker, Docker, cgroup, TUN/TAP, disk, and default port availability.
- Full Chinese and English UI copy for the implemented product chrome.
- Firecracker host installer and Docker Compose assets for local/internal deployment.
- Experimental single-node infra services: host Nomad, Postgres, Redis, MinIO, registry, Consul, and Caddy edge proxy.

## Why KVM / Firecracker Matter

KVM is the Linux kernel interface for hardware virtualization. Firecracker is a lightweight runtime that starts KVM-backed microVMs. E2B-style sandboxes rely on VM-level isolation. A single server may fail to run the runtime even if Docker works, because Docker is not a substitute for `/dev/kvm`, CPU virtualization extensions, TUN/TAP networking, and the required Linux kernel permissions.

If those checks fail, Sandbox Control can still run as a control dashboard, but the Infra page must show that Firecracker-backed sandboxes are blocked.

## Local Development

```powershell
uv sync --dev
cd apps/web
npm install
npm run build
cd ../..
uv run uvicorn sandbox_control.main:app --app-dir apps/api --host 0.0.0.0 --port 8080
```

Default development login:

- Username: `admin`
- Password: `sandbox-control-admin`

## Single-Node Infra Install

On the target Ubuntu server:

```bash
cd /opt/sandbox-control
sudo bash deploy/scripts/install-infra.sh
```

This installs Firecracker, jailer, and a host Nomad dev agent, verifies `/dev/kvm`, then starts the control-plane services with Docker Compose. The dashboard remains on `http://<server>:8080`; the Caddy edge proxy is exposed on `:8088`.

## Repository Layout

- `apps/api` - FastAPI app, in-memory Beta store, provider adapters, Codex auth manager, tests.
- `apps/web` - React/Vite TypeScript dashboard and conversation UI.
- `deploy` - Docker Compose and single-node deployment helpers.
- `docs` - bilingual architecture, deployment, and operations notes.

## Security Notes

Do not commit `.env`, real ChatGPT/Codex tokens, OpenAI API keys, Git PATs, server passwords, or copied Codex `auth.json` files. Use `SANDBOX_CONTROL_SECRET_KEY` for service-side encryption in real deployments.

## License

MIT
