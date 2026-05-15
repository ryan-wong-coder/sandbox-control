# Architecture

Sandbox Control is split into a Python control API and a React operator console.

```mermaid
flowchart LR
  Web[React/Vite UI] --> API[FastAPI API]
  API --> Store[Beta Store]
  API --> Auth[Per-user Codex Auth Manager]
  API --> Provider[Sandbox Provider Adapter]
  Provider --> Local[Single-node Experimental Runtime]
  Local --> Preflight[KVM / Firecracker Preflight]
  Local --> Firecracker[Firecracker + Jailer]
  Local --> Infra[Host Nomad, Postgres, Redis, MinIO, Registry, Consul, Edge Proxy]
```

## Runtime Boundaries

The control plane can run without Firecracker. Firecracker-backed sandboxes require Linux KVM support, exposed CPU virtualization, `/dev/kvm`, network devices, and enough disk/memory. The Infra page reports blockers instead of hiding them.

## Single-Node Infra

`deploy/scripts/install-firecracker.sh` installs Firecracker and jailer from the official release artifacts. `deploy/scripts/install-nomad.sh` installs a host Nomad dev agent managed by systemd. `deploy/scripts/install-infra.sh` runs host package setup, Firecracker/Nomad install, preflight, and the Docker Compose stack.

The compose stack includes Postgres, Redis, MinIO, registry, Consul, Caddy edge proxy, and the Sandbox Control service. Nomad runs on the host so it can use the host Docker/runtime environment directly.

## Codex Identity

Each user has an isolated Codex identity context. The primary path is ChatGPT login. OpenAI API key fallback is available when interactive login is blocked.

## Conversation Page

The conversation page is separate from the run dashboard. It presents messages, Codex tool calls, approval cards, terminal output, and file/diff context in one workflow surface.
