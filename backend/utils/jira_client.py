"""
Jira ticket ingestion — API fetch when configured, manual paste fallback.
"""

import re
from typing import Dict, List, Optional
from urllib.parse import urlparse
from datetime import datetime, timedelta

import requests

import config

_TICKET_KEY_RE = re.compile(r"([A-Z][A-Z0-9]+-\d+)")
_PROJECT_KEY_RE = re.compile(r"^([A-Z][A-Z0-9]+)-\d+$")
_SEARCH_FIELDS = [
    "summary",
    "description",
    "status",
    "labels",
    "fixVersions",
    "priority",
    "customfield_10016",  # story points (common; may vary by site)
]


def _search_field_list() -> List[str]:
    fields = list(_SEARCH_FIELDS)
    extra = (config.JIRA_TSHIRT_SIZE_FIELD or "").strip()
    if extra and extra not in fields:
        fields.append(extra)
    return fields


def parse_project_key(ticket_key: str = None, jira_url: str = None) -> Optional[str]:
    """Extract Jira project key from issue key or browse URL."""
    key = ticket_key or parse_ticket_key(jira_url or "")
    if not key:
        return None
    m = _PROJECT_KEY_RE.match(key.upper())
    return m.group(1) if m else None


_version_cache: Dict[str, tuple] = {}
_VERSION_CACHE_TTL = timedelta(minutes=5)


def list_project_versions(project_key: str) -> List[Dict]:
    """
    Return fix versions for a Jira project: name, released, releaseDate, archived.
    Results are cached briefly to avoid hammering the API during poll ingest.
    """
    if not jira_configured() or not project_key:
        return []

    now = datetime.utcnow()
    cached = _version_cache.get(project_key)
    if cached and now - cached[0] < _VERSION_CACHE_TTL:
        return cached[1]

    try:
        data = _api_get(f"/rest/api/3/project/{project_key}/versions")
    except requests.HTTPError:
        return []

    versions = []
    for item in data if isinstance(data, list) else []:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        versions.append({
            "id": item.get("id"),
            "name": name,
            "released": bool(item.get("released")),
            "releaseDate": item.get("releaseDate") or "",
            "archived": bool(item.get("archived")),
        })

    _version_cache[project_key] = (now, versions)
    return versions


def parse_ticket_key(jira_url: str) -> Optional[str]:
    if not jira_url:
        return None
    m = _TICKET_KEY_RE.search(jira_url.upper())
    return m.group(1) if m else None


def jira_configured() -> bool:
    return bool(config.JIRA_BASE_URL and config.JIRA_EMAIL and config.JIRA_API_TOKEN)


def _api_get(path: str, params: dict = None) -> dict:
    base = config.JIRA_BASE_URL.rstrip("/")
    r = requests.get(
        f"{base}{path}",
        params=params or {},
        auth=(config.JIRA_EMAIL, config.JIRA_API_TOKEN),
        headers={"Accept": "application/json"},
        timeout=45,
    )
    r.raise_for_status()
    return r.json()


def list_agile_boards(project_key_or_id: str = None, max_results: int = 50) -> List[Dict]:
    """List Jira Software boards (Agile API)."""
    if not jira_configured():
        return []
    params = {"maxResults": max_results}
    if project_key_or_id:
        params["projectKeyOrId"] = project_key_or_id
    data = _api_get("/rest/agile/1.0/board", params)
    return [
        {
            "id": b.get("id"),
            "name": b.get("name"),
            "type": b.get("type"),
            "project_key": (b.get("location") or {}).get("projectKey"),
        }
        for b in data.get("values", [])
    ]


def build_todo_jql(
    project_key: str = None,
    board_id: str = None,
    custom_jql: str = None,
) -> str:
    if custom_jql:
        return custom_jql
    if config.JIRA_TODO_JQL:
        return config.JIRA_TODO_JQL
    parts = ['statusCategory = "To Do"']
    if project_key:
        parts.append(f'project = "{project_key}"')
    elif config.JIRA_PROJECT_KEY:
        parts.append(f'project = "{config.JIRA_PROJECT_KEY}"')
    return " AND ".join(parts) + " ORDER BY updated DESC"


def resolve_default_board_id(project_key: str = None) -> Optional[str]:
    """Pick a sensible agile board id for polling (env default, then project match)."""
    if config.JIRA_BOARD_ID:
        return str(config.JIRA_BOARD_ID)
    key = project_key or config.JIRA_PROJECT_KEY
    if not key or not jira_configured():
        return None
    boards = list_agile_boards(key)
    if not boards:
        return None
    # Prefer kanban boards for swim-lane style To Do columns, then scrum.
    for preferred_type in ("kanban", "scrum"):
        match = next(
            (b for b in boards if b.get("project_key") == key and b.get("type") == preferred_type),
            None,
        )
        if match and match.get("id") is not None:
            return str(match["id"])
    first = boards[0]
    return str(first["id"]) if first.get("id") is not None else None


def search_issues(jql: str, max_results: int = 50) -> List[Dict]:
    """Run Jira search and return normalized ticket dicts."""
    if not jira_configured():
        raise RuntimeError("Jira API is not configured")
    base = config.JIRA_BASE_URL.rstrip("/")
    # Legacy GET /rest/api/3/search returns 410 on many Jira Cloud sites — use search/jql.
    r = requests.post(
        f"{base}/rest/api/3/search/jql",
        json={
            "jql": jql,
            "maxResults": max_results,
            "fields": _search_field_list(),
        },
        auth=(config.JIRA_EMAIL, config.JIRA_API_TOKEN),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        timeout=45,
    )
    r.raise_for_status()
    data = r.json()
    issues = data.get("issues") or []
    return [_normalize_issue(issue, base) for issue in issues]


def fetch_board_todo_issues(
    board_id: str = None,
    project_key: str = None,
    jql: str = None,
    max_results: int = 50,
) -> List[Dict]:
    """
    Fetch issues in the To Do category for a board/project.

    Uses agile board issues when board_id is set, otherwise JQL search.
    """
    if not jira_configured():
        raise RuntimeError("Jira API is not configured")

    todo_jql = build_todo_jql(project_key=project_key, board_id=board_id, custom_jql=jql)
    effective_board = board_id or resolve_default_board_id(project_key)

    if effective_board:
        try:
            data = _api_get(
                f"/rest/agile/1.0/board/{effective_board}/issue",
                {"maxResults": max_results, "jql": todo_jql},
            )
            base = config.JIRA_BASE_URL.rstrip("/")
            return [_normalize_issue(issue, base) for issue in data.get("issues", [])]
        except requests.HTTPError:
            pass

    return search_issues(todo_jql, max_results=max_results)


def _normalize_issue(issue: dict, base: str) -> Dict:
    key = issue.get("key") or ""
    fields = issue.get("fields") or {}
    status = fields.get("status") or {}
    description = _adf_to_text(fields.get("description"))
    ac = _extract_acceptance_criteria(description)
    fix_versions = _extract_fix_versions(fields)
    labels = fields.get("labels") or []
    story_points = fields.get("customfield_10016")
    priority = fields.get("priority") or {}
    t_shirt = _extract_tshirt_size(fields, labels)
    project_key = parse_project_key(key)
    return {
        "key": key,
        "project_key": project_key,
        "title": fields.get("summary") or key,
        "description": description,
        "acceptance_criteria": ac,
        "jira_url": f"{base}/browse/{key}" if key else "",
        "fix_versions": fix_versions,
        "fix_version": fix_versions[0] if fix_versions else "",
        "jira_status": status.get("name") or "",
        "labels": labels,
        "story_points": story_points,
        "jira_priority": priority.get("name") or priority.get("id") or "",
        "t_shirt_size": t_shirt,
        "source": "poll",
    }


def fetch_ticket(jira_url: str = None, ticket_key: str = None, manual: Dict = None) -> Dict:
    """
    Return normalized ticket dict:
    { key, title, description, acceptance_criteria, jira_url, fix_versions, fix_version, source }
    """
    key = ticket_key or parse_ticket_key(jira_url or "")
    url = jira_url or (f"{config.JIRA_BASE_URL.rstrip('/')}/browse/{key}" if key and config.JIRA_BASE_URL else "")

    if manual and (manual.get("title") or manual.get("description")):
        fix_versions = _normalize_fix_versions(manual.get("fix_versions") or manual.get("fix_version"))
        return {
            "key": key or manual.get("key", "MANUAL"),
            "title": manual.get("title", key or "Untitled ticket"),
            "description": manual.get("description", ""),
            "acceptance_criteria": manual.get("acceptance_criteria", ""),
            "jira_url": url,
            "fix_versions": fix_versions,
            "fix_version": fix_versions[0] if fix_versions else "",
            "source": "manual",
        }

    if key and jira_configured():
        return _fetch_from_api(key, url)

    if manual:
        fix_versions = _normalize_fix_versions(manual.get("fix_versions") or manual.get("fix_version"))
        return {
            "key": key or "MANUAL",
            "title": manual.get("title", key or "Untitled ticket"),
            "description": manual.get("description", ""),
            "acceptance_criteria": manual.get("acceptance_criteria", ""),
            "jira_url": url,
            "fix_versions": fix_versions,
            "fix_version": fix_versions[0] if fix_versions else "",
            "source": "manual",
        }

    raise ValueError(
        "Jira API not configured and no manual ticket content provided. "
        "Set JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN or paste ticket details."
    )


def _fetch_from_api(key: str, url: str) -> Dict:
    base = config.JIRA_BASE_URL.rstrip("/")
    api_url = f"{base}/rest/api/3/issue/{key}"
    r = requests.get(
        api_url,
        auth=(config.JIRA_EMAIL, config.JIRA_API_TOKEN),
        headers={"Accept": "application/json"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    fields = data.get("fields", {})

    title = fields.get("summary", key)
    description = _adf_to_text(fields.get("description"))
    ac = _extract_acceptance_criteria(description)
    fix_versions = _extract_fix_versions(fields)
    status = fields.get("status") or {}

    return {
        "key": key,
        "project_key": parse_project_key(key),
        "title": title,
        "description": description,
        "acceptance_criteria": ac,
        "jira_url": url or f"{base}/browse/{key}",
        "fix_versions": fix_versions,
        "fix_version": fix_versions[0] if fix_versions else "",
        "jira_status": status.get("name") or "",
        "labels": fields.get("labels") or [],
        "story_points": fields.get("customfield_10016"),
        "jira_priority": (fields.get("priority") or {}).get("name") or "",
        "t_shirt_size": _extract_tshirt_size(fields, fields.get("labels") or []),
        "source": "api",
    }


def _extract_fix_versions(fields: dict) -> List[str]:
    raw = fields.get("fixVersions") or []
    names = []
    for item in raw:
        if isinstance(item, dict) and item.get("name"):
            names.append(str(item["name"]).strip())
        elif isinstance(item, str) and item.strip():
            names.append(item.strip())
    return names


def _normalize_fix_versions(value) -> List[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        parts = [p.strip() for p in value.split(",") if p.strip()]
        return parts or ([value.strip()] if value.strip() else [])
    return []


def _extract_tshirt_size(fields: dict, labels: List[str]) -> str:
    """Read t-shirt size from configured custom field or labels."""
    import re
    field_id = (config.JIRA_TSHIRT_SIZE_FIELD or "").strip()
    if field_id:
        raw = fields.get(field_id)
        if isinstance(raw, dict):
            raw = raw.get("value") or raw.get("name") or ""
        if raw:
            return str(raw).strip().upper()

    for label in labels or []:
        m = re.match(r"^(?:size[-_]?)?(XXL|XL|XS|[SML])$", str(label).strip(), re.I)
        if m:
            return m.group(1).upper()
    return ""


def _adf_to_text(node) -> str:
    """Flatten Atlassian Document Format to plain text (best effort)."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        parts = []
        if node.get("type") == "text":
            parts.append(node.get("text", ""))
        for child in node.get("content", []):
            parts.append(_adf_to_text(child))
        if node.get("type") in ("paragraph", "heading", "listItem"):
            parts.append("\n")
        return "".join(parts)
    if isinstance(node, list):
        return "".join(_adf_to_text(c) for c in node)
    return ""


def _extract_acceptance_criteria(description: str) -> str:
    """Pull AC section from description if present."""
    if not description:
        return ""
    markers = ["acceptance criteria", "acceptance criterion", "definition of done"]
    lower = description.lower()
    for m in markers:
        idx = lower.find(m)
        if idx >= 0:
            return description[idx:].strip()
    return ""
