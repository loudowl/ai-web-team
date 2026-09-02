"""Parse LLM code blocks and apply them safely inside a worktree."""

import re
from pathlib import Path
from typing import List, Tuple

from utils.github_push import parse_developer_output


def parse_code_blocks(output: str) -> List[Tuple[str, str]]:
    """Extract (relative_path, contents) pairs from agent markdown output."""
    files = parse_developer_output(output)

    if not files:
        pattern = re.compile(
            r"(?:^|\n)#{2,4}\s+`?([^\n`]+)`?\s*\n+```[^\n]*\n(.*?)```",
            re.DOTALL,
        )
        for match in pattern.finditer(output):
            path = match.group(1).strip()
            if "." in path.split("/")[-1] or "/" in path:
                files.append((path, match.group(2)))

    if not files:
        pattern = re.compile(
            r"(?:^|\n)(?:File|Path):\s*`?([^\n`]+)`?\s*\n+```[^\n]*\n(.*?)```",
            re.DOTALL | re.IGNORECASE,
        )
        for match in pattern.finditer(output):
            files.append((match.group(1).strip(), match.group(2)))

    # De-dupe by path — last block wins
    deduped = {}
    for path, content in files:
        clean = path.strip().lstrip("/").replace("\\", "/")
        if clean and not clean.startswith("#"):
            deduped[clean] = content
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
