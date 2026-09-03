"""
GitHub integration — creates a new repo and pushes generated project files.
Uses the GitHub REST API (no git binary required).
"""

import base64
import os
import re
import requests
from typing import Dict, List, Tuple

import config

BASE = "https://api.github.com"


def _headers():
    return {
        "Authorization": f"token {config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ai-web-team/1.0",
    }


def create_repo(repo_name: str, description: str = "", private: bool = False) -> Dict:
    """
    Create a new GitHub repo, or reuse it if it already exists.

    GitHub returns 422 when a repo with the same name already exists on the
    account. Rather than failing the whole push (which made Push non-retryable),
    we fetch and reuse the existing repo so push_file() can update its contents.
    """
    payload = {
        "name":        repo_name,
        "description": description,
        "private":     private,
        "auto_init":   False,
    }
    r = requests.post(f"{BASE}/user/repos", json=payload, headers=_headers(), timeout=15)

    if r.status_code == 422:
        owner = config.GITHUB_USERNAME
        existing = requests.get(f"{BASE}/repos/{owner}/{repo_name}", headers=_headers(), timeout=10)
        if existing.status_code == 200:
            return existing.json()
        # Not an "already exists" case — surface GitHub's actual validation error.
        raise requests.HTTPError(
            f"GitHub rejected repo '{repo_name}' (422): {r.text}"
        )

    r.raise_for_status()
    return r.json()


def update_repo_description(repo_name: str, description: str) -> None:
    """Best-effort PATCH of the repo description (e.g. when reusing an existing repo)."""
    owner = config.GITHUB_USERNAME
    try:
        requests.patch(
            f"{BASE}/repos/{owner}/{repo_name}",
            json={"description": description},
            headers=_headers(),
            timeout=10,
        )
    except requests.RequestException:
        pass  # cosmetic only — never fail the push over a description


def push_file(owner: str, repo: str, path: str, content: str, message: str = "feat: initial commit") -> bool:
    """Create or update a single file in the repo via the Contents API."""
    encoded = base64.b64encode(content.encode()).decode()
    payload = {"message": message, "content": encoded}

    # Check if file already exists (to get sha for update)
    check = requests.get(f"{BASE}/repos/{owner}/{repo}/contents/{path}", headers=_headers(), timeout=10)
    if check.status_code == 200:
        payload["sha"] = check.json().get("sha")

    r = requests.put(
        f"{BASE}/repos/{owner}/{repo}/contents/{path}",
        json=payload,
        headers=_headers(),
        timeout=15,
    )
    return r.status_code in (200, 201)


def parse_developer_output(output: str) -> List[Tuple[str, str]]:
    """
    Parse the Developer agent's output and extract (filepath, code) pairs.
    Looks for patterns like:
      ### `path/to/file.ext`
      ```lang
      code
      ```
    """
    files = []
    # Match ### `filepath` followed by a code block (optional leading whitespace)
    pattern = re.compile(
        r'^\s*###\s+`([^`]+)`\s*\n\s*```[^\n]*\n(.*?)```',
        re.DOTALL | re.MULTILINE,
    )
    for match in pattern.finditer(output):
        filepath = match.group(1).strip()
        code     = match.group(2)
        files.append((filepath, code))

    # Fallback: also catch #### or ## headings with code blocks
    if not files:
        pattern2 = re.compile(
            r'(?:#{1,4})\s+[`"]?([^\n`"]+\.\w+)[`"]?\s*\n```[^\n]*\n(.*?)```',
            re.DOTALL
        )
        for match in pattern2.finditer(output):
            filepath = match.group(1).strip()
            code     = match.group(2)
            files.append((filepath, code))

    return files


def generate_readme(project_id: str, brief: str, by_agent: Dict[str, str], file_paths: List[str]) -> str:
    """
    Synthesize a comprehensive README from the agent outputs and the real file
    list (project structure, getting started, tech stack, doc links, mermaid
    architecture + user-flow diagrams). Best-effort: returns "" on any failure
    so the push falls back to the developer's own README.md.
    """
    import database as db
    from models.providers import stream_response
    from agents.prompts import README_SYSTEM, readme_prompt

    try:
        project = db.get_project(project_id) or {}
        provider = project.get("provider") or "openai"
        prompt = readme_prompt(
            brief,
            by_agent.get("pm", ""),
            by_agent.get("designer", ""),
            by_agent.get("architect", ""),
            file_paths,
        )
        chunks = [
            c for c in stream_response(
                prompt=prompt, provider=provider, agent="readme", system=README_SYSTEM
            )
        ]
        text = "".join(chunks).strip()
        # Strip an accidental wrapping ```markdown fence if the model added one.
        text = re.sub(r"^```(?:markdown|md)?\s*\n", "", text)
        text = re.sub(r"\n```$", "", text).strip()
        return text
    except Exception as e:
        print(f"[github_push] README generation failed, falling back: {e}")
        return ""


def push_project(project_id: str, repo_name: str, brief: str) -> str:
    """
    Full push: create repo + push all artifacts.
    Returns the GitHub repo URL.
    """
    import database as db

    owner = config.GITHUB_USERNAME
    artifacts = db.get_artifacts(project_id)
    by_agent = {a["agent"]: a["content"] for a in artifacts}

    # Create repo. GitHub repo descriptions must be a single line (newlines
    # trigger a 422), so derive a clean one-liner from the brief's title.
    title = next((ln.strip().lstrip("# ").strip() for ln in brief.splitlines() if ln.strip()), repo_name)
    description = title[:350]
    repo_info = create_repo(
        repo_name=repo_name,
        description=description,
        private=False,
    )
    html_url = repo_info.get("html_url", "")

    # Ensure the description is set even when reusing an existing repo
    # (POST /user/repos doesn't update description for an existing repo).
    if repo_info.get("description") != description:
        update_repo_description(repo_name, description)

    # Parse the developer's code files up front so the README generator can
    # reference the real project structure.
    dev_files = parse_developer_output(by_agent.get("developer", ""))
    dev_files = [(fp.lstrip("/").replace("..", ""), code) for fp, code in dev_files]

    # Generate and push a comprehensive README (best-effort). The list of paths
    # includes the docs we push below plus the developer's code files.
    readme_paths = ["docs/PRD.md", "docs/DESIGN.md", "docs/ARCHITECTURE.md"] + [fp for fp, _ in dev_files]
    readme = generate_readme(project_id, brief, by_agent, readme_paths)
    if readme:
        push_file(owner, repo_name, "README.md", readme, "docs: add comprehensive project README")

    # Push PM, Designer, Architect outputs as docs
    label_map = {
        "pm":        "docs/PRD.md",
        "designer":  "docs/DESIGN.md",
        "architect": "docs/ARCHITECTURE.md",
    }
    for agent, path in label_map.items():
        if agent in by_agent:
            push_file(owner, repo_name, path, by_agent[agent], f"docs: add {agent} output")

    # Push the developer's code files. Skip its own README.md when we generated
    # a dedicated one above, so the comprehensive README isn't overwritten.
    if dev_files:
        for filepath, code in dev_files:
            if readme and os.path.basename(filepath).lower() == "readme.md":
                continue
            push_file(owner, repo_name, filepath, code, "feat: initial implementation")
    elif by_agent.get("developer"):
        # Fallback: push raw developer output
        push_file(owner, repo_name, "developer_output.md", by_agent["developer"], "feat: developer output")

    db.update_project(project_id, github_url=html_url)
    return html_url
