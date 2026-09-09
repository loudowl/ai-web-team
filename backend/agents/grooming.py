"""Pre-assessed lane recommendations — t-shirt size, fix version, initial lane."""

from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Tuple

from agents.complexity import analyze_complexity, score_ticket
from utils.jira_client import list_project_versions, parse_project_key

import config

TIER_TO_TSHIRT = {
    "trivial": "XS",
    "simple": "S",
    "medium": "M",
    "complex": "L",
    "critical": "XL",
}

TSHIRT_ORDER = {"XS": 0, "S": 1, "M": 2, "L": 3, "XL": 4, "XXL": 5}

PRIORITY_ORDER = {
    "highest": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "lowest": 4,
}

_VAGUE_PHRASES = re.compile(
    r"\b(TBD|TODO|to be determined|as needed|as appropriate|somehow|maybe|might|"
    r"should work|fix it|make better|improve(?:ment)?|optimize|clean up|"
    r"etc\.?|and so on|something like|similar to|roughly|approximately)\b",
    re.I,
)
_REQUIREMENT_MARKERS = re.compile(
    r"\b(requirements?|user story|scope|must|shall|should)\b",
    re.I,
)
_BUG_MARKERS = re.compile(
    r"\b(bug|regression|defect|404|500|error|broken|fail(?:ed|ure)?|not working)\b",
    re.I,
)
_UI_MARKERS = re.compile(
    r"\b(ui|ux|css|layout|button|modal|responsive|pixel|design|visual|styling)\b",
    re.I,
)
_VERSION_IN_TEXT_RE = re.compile(r"\b(?:v|release[- ]?)?(\d+\.\d+(?:\.\d+)?)\b", re.I)


def _normalize_tshirt(raw) -> str:
    if not raw:
        return ""
    text = str(raw).strip().upper()
    for size in ("XXL", "XL", "XS", "S", "M", "L"):
        if text == size or text.endswith(size):
            return size
    return text[:4]


def _version_number_key(name: str) -> Tuple:
    nums = [int(n) for n in re.findall(r"\d+", name or "")]
    return tuple(nums) if nums else (9999,)


def _priority_rank(priority) -> int:
    key = str(priority or "").strip().lower()
    return PRIORITY_ORDER.get(key, 2)


def _extract_version_hints(ticket: Dict) -> List[str]:
    """Collect version-like strings from ticket title, description, and labels."""
    hints: List[str] = []
    chunks = [
        ticket.get("title") or "",
        ticket.get("description") or "",
        " ".join(ticket.get("labels") or []),
    ]
    for chunk in chunks:
        for match in _VERSION_IN_TEXT_RE.finditer(chunk):
            hints.append(match.group(1))
    for label in ticket.get("labels") or []:
        text = str(label).strip()
        if text:
            hints.append(text)
    return hints


def _match_hint_to_version(hints: List[str], version_names: List[str]) -> Optional[str]:
    """Match ticket hints to a project fix version name."""
    if not hints or not version_names:
        return None

    by_lower = {name.lower(): name for name in version_names}
    semver_re = re.compile(r"\d+\.\d+(?:\.\d+)?")
    for hint in hints:
        normalized = hint.strip().lower().lstrip("v")
        if not normalized:
            continue
        if normalized in by_lower:
            return by_lower[normalized]
        for lower_name, original in by_lower.items():
            if lower_name == normalized:
                return original
            if normalized in lower_name or lower_name in normalized:
                return original
            if semver_re.fullmatch(normalized):
                name_versions = semver_re.findall(lower_name)
                if normalized in name_versions:
                    return original
            hint_parts = normalized.split(".")
            name_parts = lower_name.split(".")
            if len(hint_parts) >= 2 and hint_parts[:2] == name_parts[:2]:
                return original
    return None


def _sort_unreleased_versions(versions: List[Dict]) -> List[Dict]:
    active = [v for v in versions if not v.get("released") and not v.get("archived")]
    return sorted(
        active,
        key=lambda v: (v.get("releaseDate") or "9999-12-31", _version_number_key(v.get("name") or "")),
    )


def _pick_unreleased_by_priority(versions: List[Dict], priority) -> Optional[str]:
    """Map urgency to a slot on the unreleased train (next vs later release)."""
    unreleased = _sort_unreleased_versions(versions)
    if not unreleased:
        return None
    rank = _priority_rank(priority)
    if rank <= PRIORITY_ORDER["high"]:
        return unreleased[0]["name"]
    if rank >= PRIORITY_ORDER["low"]:
        return unreleased[-1]["name"]
    mid = len(unreleased) // 2
    return unreleased[mid]["name"]


def _fallback_version_name(versions: List[Dict]) -> Optional[str]:
    """When nothing is unreleased, use the latest active version by semver."""
    active = [v for v in versions if not v.get("archived")]
    if not active:
        return None
    active.sort(key=lambda v: _version_number_key(v.get("name") or ""), reverse=True)
    return active[0]["name"]


def _resolve_project_key(ticket: Dict) -> Optional[str]:
    key = ticket.get("project_key") or parse_project_key(ticket.get("key"), ticket.get("jira_url"))
    if key:
        return key
    return (config.JIRA_PROJECT_KEY or "").strip() or None


def recommend_fix_version(ticket: Dict) -> Optional[str]:
    """
    Infer a fix version when the ticket has none set.

    Priority order:
    1. Explicit version hints in title, description, or labels
    2. Next logical unreleased project version (priority-aware)
    3. Latest active project version when all are released
    """
    if (ticket.get("fix_version") or "").strip():
        return None

    project_key = _resolve_project_key(ticket)
    versions = list_project_versions(project_key) if project_key else []
    version_names = [v["name"] for v in versions]

    hinted = _match_hint_to_version(_extract_version_hints(ticket), version_names)
    if hinted:
        return hinted

    priority = ticket.get("jira_priority")
    if isinstance(priority, dict):
        priority = priority.get("name") or priority.get("id")

    from_priority = _pick_unreleased_by_priority(versions, priority)
    if from_priority:
        return from_priority

    return _fallback_version_name(versions)


def explain_t_shirt_size_recommendation(
    ticket: Dict,
    recommended: str,
    *,
    tier: str = None,
    score: float = None,
) -> Optional[str]:
    """Human-readable rationale grounded in this ticket's actual content."""
    if not recommended or _normalize_tshirt(ticket.get("t_shirt_size")):
        return None

    analysis = analyze_complexity(ticket)
    tier = tier or analysis["tier"]
    score = score if score is not None else analysis["score"]

    story_points = analysis.get("story_points")
    if story_points is not None:
        try:
            sp = float(story_points)
            content = " ".join(analysis["content_notes"][:3])
            return (
                f"{content} "
                f"Story points ({sp:g}) are the primary sizing signal, mapping to t-shirt size {recommended}."
            )
        except (TypeError, ValueError):
            pass

    content_paragraph = " ".join(analysis["content_notes"])
    return (
        f"{content_paragraph} "
        f"Combined complexity score {score:.1f} → tier {tier} → recommended size {recommended}."
    )


def generate_creator_questions(ticket: Dict, analysis: Dict = None) -> List[str]:
    """Questions to help the ticket creator fill gaps or clarify vague specs."""
    analysis = analysis or analyze_complexity(ticket)
    questions: List[str] = []

    title = (analysis.get("title") or ticket.get("title") or "").strip()
    description = (ticket.get("description") or "").strip()
    ac = (ticket.get("acceptance_criteria") or "").strip()
    combined = f"{title}\n{description}\n{ac}"

    if not description:
        questions.append(
            "Can you add a description that explains the user problem, affected area, and desired outcome?"
        )
    elif len(description) < 150:
        questions.append(
            "The description is very short — can you expand on scope, constraints, and what 'done' looks like?"
        )

    if not ac:
        questions.append(
            "Can you add acceptance criteria with testable pass/fail conditions for QA and the developer?"
        )
    elif len(ac) < 80:
        questions.append(
            "Acceptance criteria look minimal — can you list concrete scenarios, edge cases, and verification steps?"
        )

    if description and not _REQUIREMENT_MARKERS.search(description) and not ac:
        questions.append(
            "Where are the requirements captured — user story, scope, or must-have behaviors the developer should implement?"
        )

    vague_hits = list(dict.fromkeys(m.group(0) for m in _VAGUE_PHRASES.finditer(combined)))[:4]
    if vague_hits:
        questions.append(
            "Some wording is open to interpretation ("
            + ", ".join(f'"{v}"' for v in vague_hits)
            + ") — can you replace this with specific, measurable behavior?"
        )

    if _BUG_MARKERS.search(combined):
        lower = description.lower()
        has_repro = "steps to reproduce" in lower or "step to reproduce" in lower
        has_expected = "expected result" in lower or "expected behavior" in lower
        has_actual = "actual result" in lower or "actual behavior" in lower
        if not has_repro:
            questions.append(
                "For this defect, can you add numbered steps to reproduce the issue in each affected environment?"
            )
        if not has_expected or not has_actual:
            questions.append(
                "Can you spell out expected vs actual results (including URLs, screenshots, or error messages)?"
            )

    if _UI_MARKERS.search(combined):
        lower = combined.lower()
        if not any(token in lower for token in ("figma", "mockup", "mock-up", "screenshot", "design spec")):
            questions.append(
                "This looks UI-related — can you link a Figma/mockup or attach screenshots of the target layout?"
            )

    if len(title) < 20:
        questions.append(
            "The title is very short — can you clarify the component, user flow, and failure mode in the summary?"
        )

    if not (ticket.get("fix_version") or "").strip():
        questions.append("Which fix version or release train should this ship on?")

    if analysis.get("story_points") is None and not _normalize_tshirt(ticket.get("t_shirt_size")):
        questions.append(
            "Can you add story points or a t-shirt size so the team can calibrate effort?"
        )

    if analysis.get("tier") in ("complex", "critical") and not ac:
        questions.append(
            "This looks like a larger change — can you break down phases, dependencies, or out-of-scope items?"
        )

    # De-dupe while preserving order; cap length for modal readability.
    seen = set()
    unique: List[str] = []
    for q in questions:
        key = q.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(q)
    return unique[:8]


def recommend_t_shirt_size(ticket: Dict, tier: str = None, score: float = None) -> Optional[str]:
    """Return a recommended t-shirt size when the ticket has none set."""
    if _normalize_tshirt(ticket.get("t_shirt_size")):
        return None

    existing = ticket.get("story_points")
    if existing is not None:
        try:
            sp = float(existing)
            if sp <= 1:
                return "S"
            if sp <= 2:
                return "M"
            if sp <= 5:
                return "L"
            return "XL"
        except (TypeError, ValueError):
            pass

    tier = tier or ticket.get("complexity_tier")
    if not tier:
        tier, score = score_ticket(ticket)
    return TIER_TO_TSHIRT.get(tier or "medium", "M")


def initial_board_lane(ticket: Dict) -> str:
    """Tickets without a fix version start in Pre assessed; otherwise To Do."""
    if (ticket.get("fix_version") or "").strip():
        return "todo"
    return "pre_assessed"


def groom_ticket(
    ticket: Dict,
    *,
    tier: str = None,
    score: float = None,
) -> Dict:
    """
    Compute grooming metadata for ingest/display.

    Returns dict with keys to merge into ticket row:
    board_lane, t_shirt_size, recommended_t_shirt_size, recommended_fix_version,
    jira_priority, complexity_tier, complexity_score (when scored).
    """
    if tier is None or score is None:
        analysis = analyze_complexity(ticket)
        tier = analysis["tier"]
        score = analysis["score"]
    else:
        analysis = analyze_complexity(ticket)

    fix_version = (ticket.get("fix_version") or "").strip()
    t_shirt = _normalize_tshirt(ticket.get("t_shirt_size"))
    rec_tshirt = recommend_t_shirt_size(ticket, tier=tier, score=score)
    rec_tshirt_reason = explain_t_shirt_size_recommendation(
        ticket, rec_tshirt or "", tier=tier, score=score
    )
    rec_fix = recommend_fix_version(ticket)
    creator_questions = generate_creator_questions(ticket, analysis)

    priority = ticket.get("jira_priority") or ""
    if isinstance(priority, dict):
        priority = priority.get("name") or priority.get("id") or ""

    return {
        "board_lane": initial_board_lane(ticket),
        "fix_version": fix_version or None,
        "t_shirt_size": t_shirt or None,
        "recommended_t_shirt_size": rec_tshirt,
        "recommended_t_shirt_size_reason": rec_tshirt_reason,
        "creator_questions_json": json.dumps(creator_questions) if creator_questions else None,
        "recommended_fix_version": rec_fix,
        "jira_priority": str(priority).strip() or None,
        "complexity_tier": tier,
        "complexity_score": score,
    }
