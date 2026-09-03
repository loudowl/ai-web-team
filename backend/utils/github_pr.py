"""Git commit/push and GitHub pull request creation for Jira mode."""

import re
import subprocess
import time
from pathlib import Path
from typing import List, Tuple, Optional
from urllib.parse import urlparse

import requests

import config

BASE = "https://api.github.com"


def _headers():
    return {
        "Authorization": f"token {config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "ai-web-team/1.0",
    }


def _run(cmd: list, cwd: str, timeout: int = 120) -> str:
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


def branch_name(ticket_key: str) -> str:
    key = re.sub(r"[^a-zA-Z0-9._-]+", "-", (ticket_key or "ticket").lower()).strip("-")
    prefix = (config.JIRA_BRANCH_PREFIX or "codex/").rstrip("/")
    suffix = config.JIRA_BRANCH_SUFFIX or ""
    return f"{prefix}/{key}{suffix}"


def detect_base_branch(repo_path: str) -> str:
    if config.GITHUB_BASE_BRANCH:
        return config.GITHUB_BASE_BRANCH

    try:
        ref = _run(["git", "symbolic-ref", "refs/remotes/origin/HEAD"], cwd=repo_path)
        return ref.split("/")[-1]
    except RuntimeError:
        pass

    for candidate in ("main", "master", "develop"):
        try:
            _run(["git", "rev-parse", f"origin/{candidate}"], cwd=repo_path)
            return candidate
        except RuntimeError:
            continue

    return "main"


def parse_github_remote(repo_path: str) -> Tuple[str, str]:
    url = _run(["git", "remote", "get-url", "origin"], cwd=repo_path)

    scp_match = re.match(r"^git@[^:]+:(.+)$", url)
    if scp_match:
        path = scp_match.group(1).removesuffix(".git")
        owner, repo = path.split("/", 1)
        return owner, repo

    parsed = urlparse(url)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) >= 2:
        owner, repo = parts[0], parts[1].removesuffix(".git")
        return owner, repo

    raise ValueError(f"Could not parse GitHub remote URL: {url}")


def commit_all(worktree_path: str, message: str) -> str:
    _run(["git", "add", "-A"], cwd=worktree_path)
    status = _run(["git", "status", "--porcelain"], cwd=worktree_path)
    if not status.strip():
        raise RuntimeError("No changes to commit after applying patches")
    _run(["git", "commit", "-m", message], cwd=worktree_path)
    return _run(["git", "rev-parse", "HEAD"], cwd=worktree_path)


def push_branch(worktree_path: str, branch: str) -> None:
    _run(["git", "push", "-u", "origin", branch], cwd=worktree_path, timeout=300)


def create_pull_request(
    owner: str,
    repo: str,
    title: str,
    head: str,
    base: str,
    body: str,
) -> str:
    if not config.GITHUB_TOKEN:
        raise RuntimeError("GITHUB_TOKEN is required to create pull requests")

    existing = requests.get(
        f"{BASE}/repos/{owner}/{repo}/pulls",
        params={"head": f"{owner}:{head}", "state": "open"},
        headers=_headers(),
        timeout=20,
    )
    existing.raise_for_status()
    pulls = existing.json()
    if pulls:
        return pulls[0]["html_url"]

    response = requests.post(
        f"{BASE}/repos/{owner}/{repo}/pulls",
        json={"title": title, "head": head, "base": base, "body": body},
        headers=_headers(),
        timeout=20,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"GitHub PR creation failed ({response.status_code}): {response.text}")

    return response.json()["html_url"]


def parse_pr_number(pr_url: str) -> Optional[int]:
    m = re.search(r"/pull/(\d+)", pr_url or "")
    return int(m.group(1)) if m else None


def _get_json(url: str, params: dict = None) -> list | dict:
    response = requests.get(url, params=params, headers=_headers(), timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_pr_review_feedback(owner: str, repo: str, pr_number: int) -> List[dict]:
    """
    Collect inline review comments and issue comments (incl. Copilot bot).
    Returns normalized dicts: {path, line, body, author, url, source}.
    """
    items = []

    for comment in _get_json(f"{BASE}/repos/{owner}/{repo}/pulls/{pr_number}/comments"):
        items.append({
            "path": comment.get("path"),
            "line": comment.get("line") or comment.get("original_line"),
            "body": (comment.get("body") or "").strip(),
            "author": (comment.get("user") or {}).get("login", ""),
            "url": comment.get("html_url", ""),
            "source": "review_comment",
        })

    for comment in _get_json(f"{BASE}/repos/{owner}/{repo}/issues/{pr_number}/comments"):
        items.append({
            "path": None,
            "line": None,
            "body": (comment.get("body") or "").strip(),
            "author": (comment.get("user") or {}).get("login", ""),
            "url": comment.get("html_url", ""),
            "source": "issue_comment",
        })

    # De-dupe by body prefix
    seen = set()
    unique = []
    for item in items:
        key = (item["path"], item["line"], item["body"][:120])
        if key in seen or not item["body"]:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def wait_for_copilot_feedback(owner: str, repo: str, pr_number: int, wait_sec: int) -> List[dict]:
    """Poll briefly for new Copilot/reviewer comments after PR opens."""
    if wait_sec <= 0:
        return fetch_pr_review_feedback(owner, repo, pr_number)

    deadline = time.time() + wait_sec
    last_count = 0
    while time.time() < deadline:
        comments = fetch_pr_review_feedback(owner, repo, pr_number)
        copilot = [c for c in comments if _is_bot_reviewer(c["author"])]
        if len(copilot) > last_count or (comments and time.time() > deadline - 5):
            return comments
        last_count = len(copilot)
        time.sleep(min(15, max(5, wait_sec // 6)))
    return fetch_pr_review_feedback(owner, repo, pr_number)


def is_bot_reviewer(login: str) -> bool:
    lower = (login or "").lower()
    return any(x in lower for x in ("copilot", "github-actions", "bugbot"))


def _is_bot_reviewer(login: str) -> bool:
    return is_bot_reviewer(login)


def commit_if_changed(worktree_path: str, message: str) -> bool:
    _run(["git", "add", "-A"], cwd=worktree_path)
    status = _run(["git", "status", "--porcelain"], cwd=worktree_path)
    if not status.strip():
        return False
    _run(["git", "commit", "-m", message], cwd=worktree_path)
    return True


def push_followup_commit(worktree_path: str, branch: str, message: str) -> bool:
    if commit_if_changed(worktree_path, message):
        push_branch(worktree_path, branch)
        return True
    return False


def publish_ticket_changes(
    repo_path: str,
    worktree_path: str,
    ticket_key: str,
    title: str,
    body: str,
    jira_url: str = "",
    base_branch: str = None,
) -> Tuple[str, str]:
    """
    Commit, push, and open a PR for ticket work.
    Returns (branch_name, pr_url).
    """
    branch, _ = commit_and_push_ticket(worktree_path, repo_path, ticket_key, title)
    pr_url = open_ticket_pull_request(
        repo_path=repo_path,
        branch=branch,
        ticket_key=ticket_key,
        title=title,
        body=body,
        jira_url=jira_url,
        base_branch=base_branch,
    )
    return branch, pr_url


def commit_and_push_ticket(
    worktree_path: str,
    repo_path: str,
    ticket_key: str,
    title: str,
) -> Tuple[str, str]:
    """Commit and push ticket work; returns (branch, commit_sha)."""
    branch = branch_name(ticket_key)
    commit_msg = f"{ticket_key}: {title}" if ticket_key else title
    sha = commit_all(worktree_path, commit_msg[:500])
    push_branch(worktree_path, branch)
    return branch, sha


def open_ticket_pull_request(
    repo_path: str,
    branch: str,
    ticket_key: str,
    title: str,
    body: str,
    jira_url: str = "",
    base_branch: str = None,
) -> str:
    base = base_branch or detect_base_branch(repo_path)
    owner, repo = parse_github_remote(repo_path)
    pr_title = f"{ticket_key}: {title}" if ticket_key else title
    pr_body_parts = [body.strip()] if body.strip() else []
    if jira_url:
        pr_body_parts.append(f"\n\nJira: {jira_url}")
    pr_body_parts.append(f"\n\n**Base branch:** `{base}`")
    pr_body_parts.append("\n\n---\n_Automated PR from ai-web-team Jira mode._")
    return create_pull_request(
        owner=owner,
        repo=repo,
        title=pr_title[:250],
        head=branch,
        base=base,
        body="".join(pr_body_parts)[:65000],
    )
