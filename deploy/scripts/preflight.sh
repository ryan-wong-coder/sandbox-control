#!/usr/bin/env bash
set -euo pipefail

echo "Sandbox Control single-node preflight"
echo "===================================="
echo "Kernel: $(uname -a)"
echo

check() {
  local name="$1"
  local command="$2"
  if bash -lc "$command" >/tmp/sandbox-control-check.out 2>&1; then
    echo "PASS $name"
  else
    echo "FAIL $name"
    sed 's/^/  /' /tmp/sandbox-control-check.out || true
  fi
}

check "Linux" "test \"$(uname -s)\" = Linux"
check "CPU virtualization" "grep -Eq '(vmx|svm)' /proc/cpuinfo"
check "/dev/kvm" "test -r /dev/kvm && test -w /dev/kvm"
check "cgroup" "test -d /sys/fs/cgroup"
check "TUN/TAP" "test -e /dev/net/tun"
check "Docker" "command -v docker && docker version"
check "Firecracker binary" "command -v firecracker"

echo
echo "KVM is the Linux kernel hardware virtualization interface."
echo "Firecracker needs /dev/kvm to start microVMs. Docker alone is not enough."
