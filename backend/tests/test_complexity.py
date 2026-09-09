"""Tests for heuristic complexity scoring."""

from agents.complexity import analyze_complexity, score_ticket


def test_trivial_ticket_from_short_copy_fix():
    ticket = {
        "title": "Fix typo in nav label",
        "description": "The About label has a spelling error.",
        "acceptance_criteria": "",
        "labels": ["copy"],
    }
    tier, score = score_ticket(ticket)
    assert tier == "trivial"
    assert score < 18

    analysis = analyze_complexity(ticket)
    assert analysis["content_notes"]
    assert any("Fix typo" in note or "typo" in note.lower() for note in analysis["content_notes"])


def test_complex_ticket_from_architecture_keywords():
    ticket = {
        "title": "Platform migration for auth service",
        "description": "We need an architecture refactor to migrate authentication to a new database layer with GraphQL.",
        "acceptance_criteria": "Acceptance criteria\n" + ("Must support SSO. " * 40),
        "labels": ["architecture", "epic"],
    }
    tier, score = score_ticket(ticket)
    assert tier in ("complex", "critical")
    assert score >= 55

    analysis = analyze_complexity(ticket)
    assert any("architecture" in note or "heavier work" in note for note in analysis["content_notes"])


def test_story_points_increase_score():
    ticket = {
        "title": "Implement reporting dashboard",
        "description": "Add charts for usage metrics.",
        "acceptance_criteria": "",
        "story_points": 5,
    }
    tier, score = score_ticket(ticket)
    assert score >= 20
    analysis = analyze_complexity(ticket)
    assert analysis["story_points"] == 5.0
