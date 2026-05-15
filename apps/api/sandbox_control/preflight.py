from __future__ import annotations

import os
import platform
import shutil
import socket
import subprocess
from pathlib import Path

from .schemas import ComponentHealth, InfraCheck, InfraPreflight, now_iso


def _run(command: list[str], timeout: int = 3) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        output = "\n".join(part for part in [completed.stdout, completed.stderr] if part).strip()
        return completed.returncode, output
    except Exception as exc:  # pragma: no cover - defensive diagnostics
        return 127, str(exc)


def _check_port(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def run_preflight() -> InfraPreflight:
    checks: list[InfraCheck] = []
    system = platform.system().lower()
    is_linux = system == "linux"
    checks.append(
        InfraCheck(
            id="os",
            label="Linux OS",
            status="pass" if is_linux else "fail",
            summary=platform.platform(),
            detail="E2B/Firecracker requires Linux. Windows/macOS can host the dashboard but not the microVM runtime.",
        )
    )

    cpuinfo = Path("/proc/cpuinfo")
    cpu_text = cpuinfo.read_text(errors="ignore") if cpuinfo.exists() else ""
    has_vmx = " vmx " in f" {cpu_text} "
    has_svm = " svm " in f" {cpu_text} "
    checks.append(
        InfraCheck(
            id="cpu_virtualization",
            label="CPU virtualization",
            status="pass" if has_vmx or has_svm else "fail",
            summary="VT-x/AMD-V available" if has_vmx or has_svm else "VT-x/AMD-V not detected",
            detail="KVM needs CPU virtualization extensions exposed by the host or hypervisor.",
        )
    )

    kvm_path = Path("/dev/kvm")
    checks.append(
        InfraCheck(
            id="kvm",
            label="/dev/kvm",
            status="pass" if kvm_path.exists() and os.access(kvm_path, os.R_OK | os.W_OK) else "fail",
            summary="KVM device usable" if kvm_path.exists() else "KVM device missing",
            detail="Firecracker starts microVMs through /dev/kvm. Containers alone do not provide this device.",
        )
    )

    firecracker = shutil.which("firecracker")
    checks.append(
        InfraCheck(
            id="firecracker",
            label="Firecracker",
            status="pass" if firecracker else "warn",
            summary=firecracker or "firecracker binary not found",
            detail="The binary can be installed during infra setup, but KVM must already work.",
        )
    )

    docker = shutil.which("docker")
    docker_status = "warn"
    docker_summary = "docker not found"
    if docker:
        code, output = _run(["docker", "version", "--format", "{{.Server.Version}}"])
        docker_status = "pass" if code == 0 else "warn"
        docker_summary = output or docker
    checks.append(
        InfraCheck(
            id="docker",
            label="Docker",
            status=docker_status,
            summary=docker_summary,
            detail="Docker is used for the control plane and helper services, not as the isolation boundary.",
        )
    )

    checks.extend(
        [
            InfraCheck(
                id="cgroup",
                label="cgroup",
                status="pass" if Path("/sys/fs/cgroup").exists() else "fail",
                summary="cgroup filesystem present" if Path("/sys/fs/cgroup").exists() else "cgroup missing",
                detail="Resource accounting and process isolation need cgroup support.",
            ),
            InfraCheck(
                id="tun_tap",
                label="TUN/TAP",
                status="pass" if Path("/dev/net/tun").exists() else "warn",
                summary="/dev/net/tun present" if Path("/dev/net/tun").exists() else "TUN device missing",
                detail="Sandbox networking usually needs TUN/TAP or bridge networking support.",
            ),
            InfraCheck(
                id="disk",
                label="Disk",
                status="pass" if shutil.disk_usage("/").free > 30 * 1024**3 else "warn",
                summary=f"{round(shutil.disk_usage('/').free / 1024**3)} GiB free",
                detail="Templates, snapshots and logs can consume disk quickly on a single node.",
            ),
            InfraCheck(
                id="port_8080",
                label="Port 8080",
                status="warn" if _check_port(8080) else "pass",
                summary="8080 already in use" if _check_port(8080) else "8080 available",
                detail="The dashboard listens on 8080 by default.",
            ),
        ]
    )

    statuses = [check.status for check in checks]
    overall = "fail" if "fail" in statuses else "warn" if "warn" in statuses else "pass"
    score = int((statuses.count("pass") / len(statuses)) * 100)
    return InfraPreflight(
        checked_at=now_iso(),
        overall_status=overall,
        overall_score=score,
        checks=checks,
    )


def component_health() -> list[ComponentHealth]:
    return [
        ComponentHealth(id="kvm", label="KVM", status="healthy", version="host", summary="preflight gated", sparkline=[78, 80, 83, 82, 86]),
        ComponentHealth(id="firecracker", label="Firecracker", status="healthy", version="v1.12.x", summary="microVM runtime", sparkline=[60, 64, 68, 70, 72]),
        ComponentHealth(id="nomad", label="Nomad", status="healthy", version="v1.6.4", summary="scheduler", sparkline=[50, 54, 53, 57, 61]),
        ComponentHealth(id="consul", label="Consul", status="healthy", version="v1.16.2", summary="service discovery", sparkline=[70, 72, 74, 73, 75]),
        ComponentHealth(id="postgres", label="Postgres", status="healthy", version="15.5", summary="control data", sparkline=[66, 63, 65, 67, 69]),
        ComponentHealth(id="redis", label="Redis", status="healthy", version="7.2.4", summary="events and queues", sparkline=[58, 61, 62, 64, 66]),
        ComponentHealth(id="object_store", label="Object Store", status="warn", version="MinIO", summary="low space", sparkline=[45, 44, 43, 41, 39]),
        ComponentHealth(id="registry", label="Registry", status="healthy", version="Harbor", summary="template images", sparkline=[62, 63, 65, 68, 70]),
        ComponentHealth(id="edge_proxy", label="Edge Proxy", status="healthy", version="Caddy", summary="port routing", sparkline=[80, 81, 80, 83, 84]),
    ]
