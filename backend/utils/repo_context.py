"""Format ticket + compact repo context for Jira mode agents."""

from pathlib import Path
from typing import Dict, List, Optional

import config

# Keep repo context small — must fit in Ollama num_ctx alongside output tokens.
_MAX_FILE_BYTES = 12_000
_MAX_RULES_CHARS = 24_000
_MAX_TREE_LINES = 120
_MAX_REPO_CONTEXT_CHARS = 40_000
# Analyze phase: tree + minimal rules; ticket is appended last so it survives truncation.
_MAX_ANALYZE_REPO_CHARS = 6_000
_MAX_ANALYZE_RULES_CHARS = 2_000

_RULE_SUFFIXES = {".md", ".mdc", ".txt"}
_SKIP_PATH_PARTS = (
    "/skills/",
    "/agents/",
    "/mcp/",
    "/hooks/",
    "/scripts/",
    "/docs/",
    "/references/",
    "package-lock.json",
    ".adf.json",
)


def resolve_context_root(project_path: Optional[str] = None) -> Path:
    raw = project_path or config.REPO_CONTEXT_PATH
    if not raw:
        raise ValueError("repo_context_path is required for Jira mode")
    p = Path(raw).expanduser().resolve()
    if not p.exists():
        raise ValueError(f"Repo context path does not exist: {p}")
    return p


def list_repos(root: Path) -> List[Path]:
    if (root / ".git").exists():
        return [root]
    repos = []
    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / ".git").exists():
            repos.append(child)
    return repos or [root]


def format_ticket_block(ticket: dict) -> str:
    ac = (ticket.get("acceptance_criteria") or "").strip()
    if not ac:
        ac = "See description — extract acceptance criteria from the description below."

    return f"""# ACTIVE JIRA TICKET (authoritative — implement ONLY this)

**Key:** {ticket.get("key", "N/A")}
**Title:** {ticket.get("title", "")}
**URL:** {ticket.get("jira_url", "n/a")}

## Description
{ticket.get("description", "").strip()}

## Acceptance Criteria
{ac}

Do NOT implement example content from cursor skills, templates, or unrelated tickets.
Your plan and code must directly satisfy the acceptance criteria above."""


def _read_file_safe(path: Path, max_bytes: int = _MAX_FILE_BYTES) -> str:
    try:
        if path.stat().st_size > max_bytes:
            text = path.read_text(encoding="utf-8", errors="replace")[:max_bytes]
            return text + "\n\n[... truncated ...]"
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _should_include_cursor_file(rel: str) -> bool:
    rel_lower = rel.lower().replace("\\", "/")
    if any(part in rel_lower for part in _SKIP_PATH_PARTS):
        return False
    if rel_lower.startswith("skills/"):
        return False
    if "/rules/" in rel_lower or rel_lower.endswith(".mdc"):
        return True
    if rel_lower in {".cursorrules", "agents.md", "claude.md"}:
        return True
    if rel_lower.endswith(".github/copilot-instructions.md"):
        return True
    return False


def _collect_cursor_files(repo: Path, max_rules_chars: int = _MAX_RULES_CHARS) -> List[Dict[str, str]]:
    found = []
    budget = max_rules_chars

    candidates = []
    cursor_rules = repo / ".cursor" / "rules"
    if cursor_rules.is_dir():
        candidates.extend(sorted(cursor_rules.rglob("*")))

    for name in (".cursorrules", "AGENTS.md", "CLAUDE.md"):
        p = repo / name
        if p.is_file():
            candidates.append(p)

    gh = repo / ".github" / "copilot-instructions.md"
    if gh.is_file():
        candidates.append(gh)

    seen = set()
    for p in candidates:
        if not p.is_file() or p.suffix not in _RULE_SUFFIXES and p.name not in {
            ".cursorrules", "AGENTS.md", "CLAUDE.md", "copilot-instructions.md",
        }:
            continue
        rel = str(p.relative_to(repo))
        if rel in seen or not _should_include_cursor_file(rel):
            continue
        seen.add(rel)
        content = _read_file_safe(p)
        if not content.strip():
            continue
        if len(content) > budget:
            content = content[:budget] + "\n\n[... truncated ...]"
        found.append({"path": rel, "content": content})
        budget -= len(content)
        if budget <= 0:
            break

    return found


def _tree_summary(repo: Path, max_depth: int = 2) -> str:
    lines = [repo.name + "/"]

    def walk(path: Path, prefix: str, depth: int):
        if depth > max_depth:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            return
        for i, entry in enumerate(entries):
            if entry.name in (".git", "node_modules", "__pycache__", ".venv", "dist", "build", ".cursor"):
                continue
            connector = "└── " if i == len(entries) - 1 else "├── "
            lines.append(f"{prefix}{connector}{entry.name}")
            if entry.is_dir():
                extension = "    " if i == len(entries) - 1 else "│   "
                walk(entry, prefix + extension, depth + 1)

    walk(repo, "", 0)
    return "\n".join(lines[:_MAX_TREE_LINES])


def format_repo_context(packages: List[Dict], max_chars: int = _MAX_REPO_CONTEXT_CHARS) -> str:
    parts = ["# Repository Context (conventions only — not the task)\n"]
    for pkg in packages:
        parts.append(f"\n## Repo: {pkg['name']}\n")
        parts.append(f"Path: `{pkg['path']}`\n")
        parts.append("### Directory tree (partial)\n```\n" + pkg["tree"] + "\n```\n")
        if pkg["cursor_files"]:
            parts.append("### Project rules (follow these conventions)\n")
            for f in pkg["cursor_files"]:
                parts.append(f"#### `{f['path']}`\n```\n{f['content']}\n```\n")

    text = "".join(parts)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[... repo context truncated ...]"
    return text


def format_analyze_repo_context(packages: List[Dict]) -> str:
    """Compact repo snapshot for planning — tree only, tiny rule budget."""
    parts = ["# Repository snapshot (for file paths only — NOT the task)\n"]
    for pkg in packages:
        parts.append(f"\n## Repo: {pkg['name']}\n")
        parts.append("### Directory tree (partial)\n```\n" + pkg["tree"] + "\n```\n")

    text = "".join(parts)
    if len(text) > _MAX_ANALYZE_REPO_CHARS:
        text = text[:_MAX_ANALYZE_REPO_CHARS] + "\n\n[... tree truncated ...]"
    return text


def build_repo_context(repo_context_path: str, ticket: Optional[dict] = None) -> Dict:
    root = resolve_context_root(repo_context_path)
    repos = list_repos(root)
    packages = []

    for repo in repos:
        packages.append({
            "name": repo.name,
            "path": str(repo),
            "tree": _tree_summary(repo),
            "cursor_files": _collect_cursor_files(repo),
        })

    repo_text = format_repo_context(packages)
    analyze_repo_text = format_analyze_repo_context(packages)
    ticket_text = format_ticket_block(ticket) if ticket else ""
    context_text = ticket_text
    if repo_text:
        context_text = f"{ticket_text}\n\n---\n\n{repo_text}" if ticket_text else repo_text

    return {
        "root": str(repos[0]) if len(repos) == 1 else str(root),
        "repos": packages,
        "context_text": context_text,
        "analyze_repo_text": analyze_repo_text,
        "ticket_text": ticket_text,
        "repo_text": repo_text,
    }
