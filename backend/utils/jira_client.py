"""
Jira ticket ingestion — API fetch when configured, manual paste fallback.
"""

import re
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests

import config

_TICKET_KEY_RE = re.compile(r"([A-Z][A-Z0-9]+-\d+)")


def parse_ticket_key(jira_url: str) -> Optional[str]:
    if not jira_url:
        return None
    m = _TICKET_KEY_RE.search(jira_url.upper())
    return m.group(1) if m else None


def jira_configured() -> bool:
    return bool(config.JIRA_BASE_URL and config.JIRA_EMAIL and config.JIRA_API_TOKEN)


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

    return {
        "key": key,
        "title": title,
        "description": description,
        "acceptance_criteria": ac,
        "jira_url": url or f"{base}/browse/{key}",
        "fix_versions": fix_versions,
        "fix_version": fix_versions[0] if fix_versions else "",
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
