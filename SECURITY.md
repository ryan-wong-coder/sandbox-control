# Security Policy

Sandbox Control handles high-value credentials and code execution workflows. Treat every deployment as sensitive.

## Secrets

- Never commit `.env`, API keys, PATs, ChatGPT/Codex tokens, server passwords, or Codex `auth.json`.
- Set `SANDBOX_CONTROL_SECRET_KEY` to a long random value before using real secrets.
- Prefer per-user Codex and Git credentials over shared platform-wide credentials.

## Runtime Boundaries

Single-node Firecracker support is experimental. Docker is not the sandbox boundary for untrusted code. Firecracker requires KVM, Linux kernel support, and network device support.

## Reporting

For now, report vulnerabilities through private GitHub channels or by opening a minimal issue without secrets or exploit payloads.
