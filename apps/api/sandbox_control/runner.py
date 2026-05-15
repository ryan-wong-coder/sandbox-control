from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .codex_auth import CodexAuthManager
from .schemas import RunStatus
from .settings import Settings
from .store import Store


def run_codex_job(run_id: str, settings: Settings, store: Store, codex_auth: CodexAuthManager) -> None:
    run = store.runs[run_id]
    work_root = settings.runtime_dir / "runs" / run_id
    repo_dir = work_root / "repo"
    work_root.mkdir(parents=True, exist_ok=True)

    try:
        if not run.repo.strip():
            _fail(store, run_id, "repo is required")
            return
        if not run.prompt.strip():
            _fail(store, run_id, "prompt is required")
            return

        store.set_run_status(run_id, RunStatus.cloning, progress=15, step="cloning repository")
        store.append_event(run_id, "info", "clone.started", f"cloning {run.repo}@{run.branch}")
        _clone_repo(run.repo, run.branch, repo_dir)
        store.append_event(run_id, "info", "clone.completed", str(repo_dir))

        codex_bin = shutil.which(settings.codex_command)
        if not codex_bin:
            _fail(store, run_id, f"codex command not found: {settings.codex_command}")
            return

        store.set_run_status(run_id, RunStatus.executing, progress=45, step="running codex exec")
        env = os.environ.copy()
        env["CODEX_HOME"] = str(codex_auth.user_codex_home(run.owner_id))
        api_key = store.latest_secret_value(run.owner_id, "openai_api_key")
        if api_key:
            env["OPENAI_API_KEY"] = api_key

        command = [codex_bin, "exec", "--json", run.prompt]
        store.append_event(run_id, "info", "codex.started", " ".join(command))
        process = subprocess.Popen(
            command,
            cwd=str(repo_dir),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        assert process.stdout is not None
        for line in process.stdout:
            clean = line.rstrip()
            if clean:
                store.append_event(run_id, "info", "codex.output", clean)
        code = process.wait()
        diff_summary = _collect_diff(repo_dir)
        if code == 0:
            store.set_run_status(
                run_id,
                RunStatus.review,
                progress=90,
                step="waiting for review",
                diff_summary=diff_summary,
            )
            store.append_event(run_id, "pass", "codex.completed", "codex exec exited with code 0")
        else:
            store.set_run_status(
                run_id,
                RunStatus.failed,
                progress=100,
                step=f"codex exec failed: {code}",
                diff_summary=diff_summary,
            )
            store.append_event(run_id, "error", "codex.failed", f"codex exec exited with code {code}")
    except Exception as exc:  # pragma: no cover - operational guardrail
        _fail(store, run_id, str(exc))


def _clone_repo(repo: str, branch: str, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    source = _repo_source(repo)
    command = ["git", "clone", "--depth", "1"]
    if branch:
        command.extend(["--branch", branch])
    command.extend([source, str(target)])
    completed = subprocess.run(command, text=True, capture_output=True, check=False, timeout=300)
    if completed.returncode != 0:
        output = "\n".join(part for part in [completed.stdout, completed.stderr] if part).strip()
        raise RuntimeError(output or f"git clone failed with code {completed.returncode}")


def _repo_source(repo: str) -> str:
    repo = repo.strip()
    path = Path(repo)
    if path.exists():
        return str(path)
    if repo.startswith(("http://", "https://", "git@")):
        return repo
    if "/" in repo and " " not in repo:
        return f"https://github.com/{repo}.git"
    return repo


def _collect_diff(repo_dir: Path) -> dict[str, object]:
    stat = subprocess.run(["git", "diff", "--numstat"], cwd=repo_dir, text=True, capture_output=True, check=False)
    hunks: list[dict[str, object]] = []
    added = 0
    removed = 0
    files_changed = 0
    first_file = ""
    for line in stat.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            files_changed += 1
            if not first_file:
                first_file = parts[2]
            if parts[0].isdigit():
                added += int(parts[0])
            if parts[1].isdigit():
                removed += int(parts[1])

    diff = subprocess.run(["git", "diff", "--unified=0"], cwd=repo_dir, text=True, capture_output=True, check=False)
    current_line = 0
    for line in diff.stdout.splitlines():
        if line.startswith("@@"):
            marker = line.split("+", 1)[-1].split(" ", 1)[0].split(",", 1)[0]
            current_line = int(marker) if marker.isdigit() else 0
        elif line.startswith("+") and not line.startswith("+++"):
            hunks.append({"line": current_line, "kind": "add", "text": line[1:160]})
            current_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            hunks.append({"line": current_line, "kind": "remove", "text": line[1:160]})
        if len(hunks) >= 40:
            break

    return {
        "file": first_file,
        "added": added,
        "removed": removed,
        "files_changed": files_changed,
        "hunks": hunks,
    }


def _fail(store: Store, run_id: str, message: str) -> None:
    store.set_run_status(run_id, RunStatus.failed, progress=100, step="failed")
    store.append_event(run_id, "error", "run.failed", message)
