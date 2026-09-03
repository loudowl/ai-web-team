"""
Map Jira fixVersion values to collab release branches for worktrees and PR bases.
"""

import re
from typing import List, Optional, Tuple

import config
from utils.github_pr import _run, detect_base_branch


_VERSION_RE = re.compile(r"(\d+\.\d+(?:\.\d+)?(?:\.\d+)?)")


def parse_release_version(fix_version_name: str) -> Optional[str]:
    """Extract a semver-like release token from a Jira fixVersion name."""
    name = (fix_version_name or "").strip()
    if not name:
        return None

    lower = name.lower()
    for prefix in (
        "post-fts web ",
        "post-fts-web ",
        "fts web ",
        "fts-web ",
        "post-",
    ):
        if lower.startswith(prefix):
            name = name[len(prefix):].strip()
            lower = name.lower()
            break

    match = _VERSION_RE.search(name)
    return match.group(1) if match else None


def fix_version_to_collab_branch(fix_version_name: str) -> Optional[str]:
    """Convert a Jira fixVersion label to a collab release branch name."""
    version = parse_release_version(fix_version_name)
    if not version:
        return None
    prefix = (config.JIRA_COLLAB_BRANCH_PREFIX or "collab/release-").rstrip("/")
    if not prefix.endswith("-"):
        prefix = f"{prefix}-"
    return f"{prefix}{version}"


def remote_branch_exists(repo_path: str, branch: str) -> bool:
    try:
        _run(["git", "rev-parse", f"origin/{branch}"], cwd=repo_path)
        return True
    except RuntimeError:
        return False


def resolve_collab_base_branch(
    repo_path: str,
    fix_versions: Optional[List[str]] = None,
) -> Tuple[str, str]:
    """
    Pick the git base branch for a ticket.

    Returns (branch_name, reason).
    Prefers a fixVersion-derived collab branch that exists on origin.
    Falls back to GITHUB_BASE_BRANCH / origin default when no fixVersion is set.
    """
    fix_versions = [v for v in (fix_versions or []) if v]

    candidates: List[Tuple[str, str]] = []
    seen = set()
    for fv in fix_versions:
        branch = fix_version_to_collab_branch(fv)
        if branch and branch not in seen:
            seen.add(branch)
            candidates.append((branch, fv))

    if candidates:
        try:
            _run(["git", "fetch", "origin", "--prune"], cwd=repo_path, timeout=180)
        except RuntimeError:
            pass

        for branch, fv in candidates:
            if remote_branch_exists(repo_path, branch):
                return branch, f"fixVersion {fv!r}"

        branch, fv = candidates[0]
        return branch, f"fixVersion {fv!r} (not found on origin — fetched best match)"

    default = detect_base_branch(repo_path)
    if config.GITHUB_BASE_BRANCH:
        return default, "GITHUB_BASE_BRANCH override (no fixVersion on ticket)"
    return default, "origin default (no fixVersion on ticket)"
