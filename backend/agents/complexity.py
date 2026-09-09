"""Heuristic complexity scoring for Jira tickets (ingest-time triage)."""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

_TIERS = ("trivial", "simple", "medium", "complex", "critical")

_COMPLEX_KEYWORDS = re.compile(
    r"\b(refactor|architecture|migrate|migration|performance|security|"
    r"breaking|epic|platform|infrastructure|multi-?repo|database|graphql)\b",
    re.I,
)
_SIMPLE_KEYWORDS = re.compile(
    r"\b(typo|copy|text|label|css|spacing|color|wording|rename|remove\s+log)\b",
    re.I,
)


def _story_points(ticket: Dict):
    raw = ticket.get("story_points")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _truncate(text: str, limit: int = 110) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _find_keyword_matches(pattern: re.Pattern, text: str, limit: int = 4) -> List[str]:
    seen = []
    for match in pattern.finditer(text or ""):
        word = match.group(0).lower()
        if word not in seen:
            seen.append(word)
        if len(seen) >= limit:
            break
    return seen


def analyze_complexity(ticket: Dict) -> Dict:
    """
    Score a ticket and collect content-specific signals for user-facing explanations.

    Returns tier, score, content_notes (list of sentences), and scoring inputs.
    """
    title = (ticket.get("title") or "").strip()
    description = (ticket.get("description") or "").strip()
    ac = (ticket.get("acceptance_criteria") or "").strip()
    labels = [str(x).strip() for x in (ticket.get("labels") or []) if str(x).strip()]
    story_points = _story_points(ticket)

    text = f"{title}\n{description}\n{ac}"
    text_len = len(text)
    ac_len = len(ac)

    score = 0.0
    score += min(text_len / 80, 25)
    score += min(ac_len / 40, 20)
    score += min(len(labels) * 3, 9)

    content_notes: List[str] = []

    if title:
        content_notes.append(f'Ticket "{_truncate(title)}" was analyzed.')

    if description:
        if len(description) < 200:
            content_notes.append(
                f"The description is brief ({len(description)} characters), which usually indicates a smaller change."
            )
        elif len(description) > 1200:
            content_notes.append(
                f"The description is detailed ({len(description)} characters), suggesting broader scope or more verification work."
            )
        else:
            content_notes.append(
                f"The description is moderate length ({len(description)} characters) with enough detail to estimate effort."
            )

        lower_desc = description.lower()
        if any(marker in lower_desc for marker in ("steps to reproduce", "expected result", "actual result")):
            content_notes.append(
                "The write-up includes structured repro / expected-vs-actual sections typical of a bounded defect fix."
            )
        if "regression" in lower_desc:
            content_notes.append("The ticket is flagged as a regression, which can add validation effort even for small fixes.")

    if ac:
        content_notes.append(
            f"Acceptance criteria are present ({ac_len} characters), starting with: "
            f'"{_truncate(ac, 90)}"'
        )
    else:
        content_notes.append(
            "No acceptance criteria section was found, so sizing relies more on title and description signals."
        )

    simple_in_title = _find_keyword_matches(_SIMPLE_KEYWORDS, title)
    simple_in_body = _find_keyword_matches(_SIMPLE_KEYWORDS, text[:600])
    simple_hits = list(dict.fromkeys(simple_in_title + simple_in_body))
    if simple_hits:
        where = "title" if simple_in_title else "description"
        content_notes.append(
            f"Scope looks localized — wording in the {where} matches {', '.join(simple_hits)}, "
            "which points to a smaller change."
        )

    complex_hits = _find_keyword_matches(_COMPLEX_KEYWORDS, text)
    if complex_hits:
        content_notes.append(
            f"The content references heavier work themes ({', '.join(complex_hits)}), increasing estimated effort."
        )

    label_lower = [l.lower() for l in labels]
    if labels:
        content_notes.append(f"Jira labels: {', '.join(labels[:6])}" + ("…" if len(labels) > 6 else "") + ".")
    if any(l in label_lower for l in ("epic", "architecture", "tech-debt")):
        content_notes.append("Labels such as epic/architecture/tech-debt suggest a larger body of work.")
    if any(l in label_lower for l in ("bug", "hotfix", "copy")):
        content_notes.append("Bug/hotfix/copy labels nudge the estimate toward a smaller, targeted change.")

    if story_points is not None:
        score += min(story_points * 4, 24)
        content_notes.append(f"Jira story points are set to {story_points:g}.")

    if _SIMPLE_KEYWORDS.search(title) or _SIMPLE_KEYWORDS.search(text[:400]):
        score -= 12
    if _COMPLEX_KEYWORDS.search(text):
        score += 18
    if any(l in label_lower for l in ("epic", "architecture", "tech-debt")):
        score += 12
    if any(l in label_lower for l in ("bug", "hotfix", "copy")):
        score -= 4

    score = max(0.0, min(100.0, score))

    if score < 18:
        tier = "trivial"
    elif score < 35:
        tier = "simple"
    elif score < 55:
        tier = "medium"
    elif score < 75:
        tier = "complex"
    else:
        tier = "critical"

    return {
        "tier": tier,
        "score": round(score, 1),
        "title": title,
        "description_len": len(description),
        "acceptance_criteria_len": ac_len,
        "story_points": story_points,
        "labels": labels,
        "content_notes": content_notes,
    }


def score_ticket(ticket: Dict) -> Tuple[str, float]:
    """
    Return (tier, score) where score is 0–100.

    Uses title, description, acceptance criteria, labels, and story points when present.
    """
    analysis = analyze_complexity(ticket)
    return analysis["tier"], analysis["score"]
