"""
Git worktree management — one isolated worktree per Jira ticket for parallel agents.
"""

import subprocess
from pathlib import Path
from typing import Optional

import config
from utils.github_pr import branch_name, detect_base_branch


def _run(cmd: list, cwd: str = None, timeout: int = 120) -> str:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"git failed: {cmd}")
    return result.stdout.strip()


def worktree_base() -> Path:
    base = Path(config.WORKTREE_BASE)
    if not base.is_absolute():
        base = Path(__file__).resolve().parent.parent / base
    base.mkdir(parents=True, exist_ok=True)
    return base


def worktree_dest(project_id: str, ticket_id: str) -> Path:
    return (worktree_base() / project_id / ticket_id).resolve()


def ensure_worktree(
    repo_path: str,
    project_id: str,
    ticket_id: str,
    ticket_key: str = None,
) -> str:
    """
    Create or return existing worktree path for a ticket.
    Layout: {WORKTREE_BASE}/{project_id}/{ticket_id}/
    """
    repo = Path(repo_path).resolve()
    dest = worktree_dest(project_id, ticket_id)

    if not (repo / ".git").exists():
        dest.mkdir(parents=True, exist_ok=True)
        return str(dest)

    if dest.exists() and any(dest.iterdir()):
        return str(dest)

    if dest.exists():
        dest.rmdir()

    branch = branch_name(ticket_key or ticket_id)
    base_branch = detect_base_branch(str(repo))

    try:
        _run(["git", "fetch", "origin", base_branch], cwd=str(repo), timeout=180)
    except RuntimeError:
        pass

    try:
        _run(["git", "worktree", "prune"], cwd=str(repo))
    except RuntimeError:
        pass

    start_point = f"origin/{base_branch}"
    try:
        _run(["git", "rev-parse", start_point], cwd=str(repo))
    except RuntimeError:
        start_point = base_branch

    try:
        _run(
            ["git", "worktree", "add", "-B", branch, str(dest), start_point],
            cwd=str(repo),
        )
    except RuntimeError:
        try:
            _run(["git", "worktree", "add", str(dest), branch], cwd=str(repo))
        except RuntimeError as e:
            raise RuntimeError(f"Could not create worktree for {ticket_key or ticket_id}: {e}") from e

    return str(dest)


def remove_worktree(worktree_path: str, repo_path: str = None):
    """Best-effort cleanup."""
    wt = Path(worktree_path).resolve()
    if not wt.exists():
        return
    if repo_path and Path(repo_path).resolve().joinpath(".git").exists():
        try:
            _run(["git", "worktree", "remove", "--force", str(wt)], cwd=str(Path(repo_path).resolve()))
            return
        except RuntimeError:
            pass
    import shutil
    shutil.rmtree(wt, ignore_errors=True)
