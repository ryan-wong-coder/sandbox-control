#!/usr/bin/env bash
set -euo pipefail

ARCH="$(uname -m)"
case "$ARCH" in
  x86_64) NOMAD_ARCH="amd64" ;;
  aarch64) NOMAD_ARCH="arm64" ;;
  *) echo "Unsupported architecture: $ARCH" >&2; exit 1 ;;
esac

NOMAD_VERSION="${NOMAD_VERSION:-1.11.3}"
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ca-certificates curl unzip

curl -fsSL "https://releases.hashicorp.com/nomad/${NOMAD_VERSION}/nomad_${NOMAD_VERSION}_linux_${NOMAD_ARCH}.zip" -o "$tmpdir/nomad.zip"
unzip -p "$tmpdir/nomad.zip" nomad > /usr/local/bin/nomad
chmod 0755 /usr/local/bin/nomad

mkdir -p /opt/sandbox-control/.nomad
cat >/etc/systemd/system/sandbox-control-nomad.service <<'UNIT'
[Unit]
Description=Sandbox Control Nomad dev agent
After=network-online.target docker.service
Wants=network-online.target docker.service

[Service]
Environment=NOMAD_SKIP_DOCKER_IMAGE_WARN=1
ExecStart=/usr/local/bin/nomad agent -dev -bind=0.0.0.0 -data-dir=/opt/sandbox-control/.nomad
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now sandbox-control-nomad.service
nomad version
