"""
Git worktree management — one isolated worktree per Jira ticket for parallel agents.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional

import config


def _run(cmd: list, cwd: str = None) -> str:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"git failed: {cmd}")
    return result.stdout.strip()


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
    if not (repo / ".git").exists():
        # Non-git tree — use a copy directory name without git worktree
        base = Path(config.WORKTREE_BASE) / project_id / ticket_id
        base.mkdir(parents=True, exist_ok=True)
        return str(base)

    branch = f"jira/{project_id}/{ticket_key or ticket_id}"
    dest = Path(config.WORKTREE_BASE) / project_id / ticket_id
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists() and any(dest.iterdir()):
        return str(dest)

    dest.mkdir(parents=True, exist_ok=True)

    # Prune stale worktree registrations
    try:
        _run(["git", "worktree", "prune"], cwd=str(repo))
    except RuntimeError:
        pass

    try:
        _run(["git", "worktree", "add", "-B", branch, str(dest), "HEAD"], cwd=str(repo))
    except RuntimeError:
        # Branch may exist — try checkout existing
        try:
            _run(["git", "worktree", "add", str(dest), branch], cwd=str(repo))
        except RuntimeError as e:
            raise RuntimeError(f"Could not create worktree for {ticket_key or ticket_id}: {e}") from e

    return str(dest)


def remove_worktree(worktree_path: str, repo_path: str = None):
    """Best-effort cleanup."""
    wt = Path(worktree_path)
    if not wt.exists():
        return
    if repo_path and Path(repo_path).joinpath(".git").exists():
        try:
            _run(["git", "worktree", "remove", "--force", str(wt)], cwd=repo_path)
            return
        except RuntimeError:
            pass
    import shutil
    shutil.rmtree(wt, ignore_errors=True)
