"""Run project linters inside a worktree and return structured results."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import config


@dataclass
class LintResult:
    ok: bool
    output: str
    command: str
    files: List[str]


def _run(cmd: List[str], cwd: str, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _repo_has_npm(cwd: str) -> bool:
    return Path(cwd, "package.json").is_file()


def _eslint_cmd(extra: List[str], files: Optional[List[str]] = None) -> List[str]:
    """Prefer direct eslint with JSON output for parsing."""
    cmd = [
        "npx", "eslint",
        "--ext", ".ts,.js,.vue",
        "--ignore-path", ".gitignore",
        "--ignore-pattern", "static/vendor/**",
        "--format", "json",
    ]
    cmd.extend(extra)
    if files:
        cmd.extend(files)
    else:
        cmd.append(".")
    return cmd


def _format_eslint_json(raw: str) -> str:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw.strip()

    lines = []
    for entry in data:
        path = entry.get("filePath", "")
        rel = path
        for msg in entry.get("messages", []):
            line = msg.get("line", "?")
            col = msg.get("column", "?")
            rule = msg.get("ruleId") or "eslint"
            severity = "error" if msg.get("severity") == 2 else "warn"
            text = msg.get("message", "")
            lines.append(f"{rel}:{line}:{col} [{severity}] {rule} — {text}")
    return "\n".join(lines) if lines else raw.strip()


def _prepare_lint_cwd(worktree_path: str, primary_repo: str = None) -> str:
    """Use worktree for lint; symlink node_modules from primary repo when missing."""
    wt = Path(worktree_path).resolve()
    if (wt / "node_modules").exists() or not primary_repo:
        return str(wt)
    primary = Path(primary_repo).resolve()
    nm = primary / "node_modules"
    link = wt / "node_modules"
    if nm.is_dir() and not link.exists():
        try:
            link.symlink_to(nm, target_is_directory=True)
        except OSError:
            pass
    return str(wt)


def run_lint_fix(
    worktree_path: str,
    files: Optional[List[str]] = None,
    primary_repo: str = None,
) -> LintResult:
    """Run auto-fix (eslint --fix or npm run lint:fix)."""
    cwd = _prepare_lint_cwd(worktree_path, primary_repo)
    if not _repo_has_npm(cwd):
        return LintResult(True, "No package.json — skipping lint fix", "", files or [])

    fix_cmd = (config.JIRA_LINT_FIX_COMMAND or "npm run lint:fix").split()
    if files and fix_cmd[0] in ("npm", "npx"):
        cmd = fix_cmd + ["--"] + files
    else:
        cmd = _eslint_cmd(["--fix"], files) if not config.JIRA_LINT_FIX_COMMAND else fix_cmd

    proc = _run(cmd, cwd=cwd)
    output = (proc.stdout or proc.stderr or "").strip()
    return LintResult(proc.returncode == 0, output, " ".join(cmd), files or [])


def run_lint(
    worktree_path: str,
    files: Optional[List[str]] = None,
    primary_repo: str = None,
) -> LintResult:
    """Run linter and return failure output for the agent."""
    cwd = _prepare_lint_cwd(worktree_path, primary_repo)
    if not _repo_has_npm(cwd):
        return LintResult(True, "No package.json — skipping lint", "", files or [])

    if config.JIRA_LINT_COMMAND and not config.JIRA_LINT_COMMAND.startswith("npx"):
        cmd = config.JIRA_LINT_COMMAND.split()
        if files:
            cmd = cmd + ["--"] + files if cmd[0] in ("npm", "npx") else cmd + files
        proc = _run(cmd, cwd=cwd)
        output = (proc.stdout or proc.stderr or "").strip()
        return LintResult(proc.returncode == 0, output, " ".join(cmd), files or [])

    cmd = _eslint_cmd([], files)
    proc = _run(cmd, cwd=cwd)
    raw = (proc.stdout or proc.stderr or "").strip()
    output = _format_eslint_json(raw) if raw.startswith("[") else raw
    return LintResult(proc.returncode == 0, output, " ".join(cmd), files or [])
