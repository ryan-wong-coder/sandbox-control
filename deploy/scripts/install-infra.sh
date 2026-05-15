#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root so Firecracker can use /dev/kvm and Docker can manage host networking." >&2
  exit 1
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ca-certificates curl tar iproute2 iptables openssl

bash deploy/scripts/install-firecracker.sh

if [ ! -f .env ]; then
  cp .env.example .env
fi

if grep -q '^SANDBOX_CONTROL_SECRET_KEY=change-me-to-a-long-random-value$' .env; then
  secret_key="$(openssl rand -base64 48)"
  sed -i "s|^SANDBOX_CONTROL_SECRET_KEY=.*$|SANDBOX_CONTROL_SECRET_KEY=${secret_key}|" .env
fi

chmod +x deploy/scripts/preflight.sh
bash deploy/scripts/preflight.sh || true

COMPOSE_PROGRESS=plain docker compose --progress plain -f deploy/compose.yml up -d --build
docker compose -f deploy/compose.yml ps
