"""Parse LLM code blocks and apply them safely inside a worktree."""

import re
from pathlib import Path
from typing import List, Tuple

from utils.github_push import parse_developer_output

# Generated/build output — never patch these even if the model cites them.
_BLOCKED_PATH_PREFIXES = (
    ".nuxt/",
    "node_modules/",
    "dist/",
    "build/",
    ".output/",
)


def _normalize_markdown(output: str) -> str:
    """Codestral often indents headings; strip so ### `path` lines parse."""
    fixed = []
    for line in output.splitlines():
        m = re.match(r"^(\s+)(#{1,4}\s+`.+`.*)$", line)
        fixed.append(m.group(2) if m else line)
    return "\n".join(fixed)


def _clean_rel_path(path: str) -> str:
    clean = path.strip().lstrip("/").replace("\\", "/")
    parts = [p for p in clean.split("/") if p]
    # Drop accidental repo folder prefix: fts-foxnews.com/components/...
    if len(parts) > 1 and "." in parts[0] and not parts[0].startswith("."):
        parts = parts[1:]
    return "/".join(parts)


def _is_allowed_path(rel: str) -> bool:
    lower = rel.lower()
    return not any(lower.startswith(p) for p in _BLOCKED_PATH_PREFIXES)


def parse_code_blocks(output: str) -> List[Tuple[str, str]]:
    """Extract (relative_path, contents) pairs from agent markdown output."""
    text = _normalize_markdown(output)
    files = parse_developer_output(text)

    if not files:
        pattern = re.compile(
            r"(?:^|\n)\s*#{2,4}\s+`?([^\n`]+)`?\s*\n+\s*```[^\n]*\n(.*?)```",
            re.DOTALL,
        )
        for match in pattern.finditer(text):
            path = match.group(1).strip()
            if "." in path.split("/")[-1] or "/" in path:
                files.append((path, match.group(2)))

    if not files:
        pattern = re.compile(
            r"(?:^|\n)\s*(?:File|Path):\s*`?([^\n`]+)`?\s*\n+\s*```[^\n]*\n(.*?)```",
            re.DOTALL | re.IGNORECASE,
        )
        for match in pattern.finditer(text):
            files.append((match.group(1).strip(), match.group(2)))

    # De-dupe by path — last block wins; drop build artifacts
    deduped = {}
    for path, content in files:
        clean = _clean_rel_path(path)
        if clean and not clean.startswith("#") and _is_allowed_path(clean):
            deduped[clean] = content.strip() + ("\n" if content.strip() else "")
    return list(deduped.items())


def apply_patches(worktree_path: str, files: List[Tuple[str, str]]) -> List[str]:
    """Write parsed files into the worktree. Returns relative paths written."""
    if not files:
        raise ValueError("No file patches to apply")

    root = Path(worktree_path).resolve()
    if not root.exists():
        raise ValueError(f"Worktree does not exist: {root}")

    written: List[str] = []
    for rel_path, content in files:
        rel = rel_path.strip().lstrip("/").replace("\\", "/")
        parts = [p for p in rel.split("/") if p and p != "."]
        if ".." in parts:
            raise ValueError(f"Unsafe path in patch: {rel_path}")

        target = root.joinpath(*parts).resolve()
        if target != root and root not in target.parents:
            raise ValueError(f"Path escapes worktree: {rel_path}")

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append("/".join(parts))

    return written
