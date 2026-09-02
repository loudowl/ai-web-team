"""
Repository context builder — scans repo roots and reads .cursor/* rules for agent context.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

import config

# Files/dirs to always include when present
_CURSOR_GLOBS = [
    ".cursor/rules/**",
    ".cursorrules",
    "AGENTS.md",
    "CLAUDE.md",
    ".github/copilot-instructions.md",
]

_MAX_FILE_BYTES = 48_000
_MAX_TOTAL_CHARS = 120_000


def resolve_context_root(project_path: Optional[str] = None) -> Path:
    raw = project_path or config.REPO_CONTEXT_PATH
    if not raw:
        raise ValueError("repo_context_path is required for Jira mode")
    p = Path(raw).expanduser().resolve()
    if not p.exists():
        raise ValueError(f"Repo context path does not exist: {p}")
    return p


def list_repos(root: Path) -> List[Path]:
    """If root is a single repo, return [root]. If it contains git repos, return each."""
    if (root / ".git").exists():
        return [root]
    repos = []
    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / ".git").exists():
            repos.append(child)
    if repos:
        return repos
    # Not a git mono-root — treat as opaque source tree
    return [root]


def _read_file_safe(path: Path) -> str:
    try:
        if path.stat().st_size > _MAX_FILE_BYTES:
            return f"[file too large: {path.name}]"
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _collect_cursor_files(repo: Path) -> List[Dict[str, str]]:
    found = []
    cursor_dir = repo / ".cursor"
    if cursor_dir.is_dir():
        for p in sorted(cursor_dir.rglob("*")):
            if p.is_file() and p.suffix in (".md", ".mdc", ".txt", ".json", ""):
                rel = p.relative_to(repo)
                found.append({"path": str(rel), "content": _read_file_safe(p)})

    for name in (".cursorrules", "AGENTS.md", "CLAUDE.md"):
        p = repo / name
        if p.is_file():
            found.append({"path": name, "content": _read_file_safe(p)})

    gh = repo / ".github" / "copilot-instructions.md"
    if gh.is_file():
        found.append({"path": str(gh.relative_to(repo)), "content": _read_file_safe(gh)})

    return found


def _tree_summary(repo: Path, max_depth: int = 3) -> str:
    lines = []
    root_name = repo.name

    def walk(path: Path, prefix: str, depth: int):
        if depth > max_depth:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            return
        for i, entry in enumerate(entries):
            if entry.name in (".git", "node_modules", "__pycache__", ".venv", "dist", "build"):
                continue
            connector = "└── " if i == len(entries) - 1 else "├── "
            lines.append(f"{prefix}{connector}{entry.name}")
            if entry.is_dir():
                extension = "    " if i == len(entries) - 1 else "│   "
                walk(entry, prefix + extension, depth + 1)

    lines.append(root_name + "/")
    walk(repo, "", 0)
    return "\n".join(lines[:200])


def build_repo_context(repo_context_path: str, ticket_text: str = "") -> Dict:
    """
    Build context package for senior dev agent.
    Returns { repos: [{name, tree, cursor_files}], context_text }
    """
    root = resolve_context_root(repo_context_path)
    repos = list_repos(root)
    packages = []
    total_chars = 0

    for repo in repos:
        cursor_files = _collect_cursor_files(repo)
        tree = _tree_summary(repo)
        packages.append({
            "name": repo.name,
            "path": str(repo),
            "tree": tree,
            "cursor_files": cursor_files,
        })
        total_chars += len(tree) + sum(len(f["content"]) for f in cursor_files)

    context_text = format_context_text(packages, ticket_text)
    if len(context_text) > _MAX_TOTAL_CHARS:
        context_text = context_text[:_MAX_TOTAL_CHARS] + "\n\n[... context truncated ...]"

    return {
        "root": str(root),
        "repos": packages,
        "context_text": context_text,
    }


def format_context_text(packages: List[Dict], ticket_text: str = "") -> str:
    parts = ["# Repository Context\n"]
    for pkg in packages:
        parts.append(f"\n## Repo: {pkg['name']}\n")
        parts.append(f"Path: `{pkg['path']}`\n")
        parts.append("### Directory tree\n```\n" + pkg["tree"] + "\n```\n")
        if pkg["cursor_files"]:
            parts.append("### Cursor / agent rules\n")
            for f in pkg["cursor_files"]:
                parts.append(f"#### `{f['path']}`\n```\n{f['content']}\n```\n")
    if ticket_text:
        parts.append(f"\n## Ticket keywords (for file search)\n{ticket_text[:500]}\n")
    return "".join(parts)
