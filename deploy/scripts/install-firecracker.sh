#!/usr/bin/env bash
set -euo pipefail

ARCH="$(uname -m)"
case "$ARCH" in
  x86_64|aarch64) ;;
  *) echo "Unsupported architecture: $ARCH" >&2; exit 1 ;;
esac

if [ ! -e /dev/kvm ]; then
  modprobe kvm 2>/dev/null || true
fi

if [ ! -e /dev/kvm ]; then
  echo "ERROR: /dev/kvm is missing. Firecracker cannot run on this host." >&2
  exit 2
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ca-certificates curl tar

release_url="https://github.com/firecracker-microvm/firecracker/releases"
latest="${FIRECRACKER_VERSION:-$(basename "$(curl -fsSLI -o /dev/null -w '%{url_effective}' "${release_url}/latest")")}"
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

curl -fsSL "${release_url}/download/${latest}/firecracker-${latest}-${ARCH}.tgz" | tar -xz -C "$tmpdir"
release_dir="$tmpdir/release-${latest}-${ARCH}"

install -m 0755 "$release_dir/firecracker-${latest}-${ARCH}" /usr/local/bin/firecracker
if [ -f "$release_dir/jailer-${latest}-${ARCH}" ]; then
  install -m 0755 "$release_dir/jailer-${latest}-${ARCH}" /usr/local/bin/jailer
fi

firecracker --version
if command -v jailer >/dev/null 2>&1; then
  jailer --version || true
fi
