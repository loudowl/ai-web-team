"""Tests for Pre assessed grooming helpers."""

import json
from unittest.mock import patch

from agents.grooming import (
    generate_creator_questions,
    groom_ticket,
    initial_board_lane,
    recommend_fix_version,
    recommend_t_shirt_size,
)


def test_initial_board_lane_without_fix_version():
    assert initial_board_lane({"fix_version": ""}) == "pre_assessed"
    assert initial_board_lane({}) == "pre_assessed"


def test_initial_board_lane_with_fix_version():
    assert initial_board_lane({"fix_version": "Release 2.0"}) == "todo"


def test_recommend_t_shirt_from_story_points():
    assert recommend_t_shirt_size({"story_points": 1}) == "S"
    assert recommend_t_shirt_size({"story_points": 3}) == "L"
    assert recommend_t_shirt_size({"t_shirt_size": "M"}) is None


def test_recommend_t_shirt_from_complexity_tier():
    assert recommend_t_shirt_size({}, tier="trivial", score=10.0) == "XS"
    assert recommend_t_shirt_size({}, tier="complex", score=60.0) == "L"


@patch("agents.grooming.list_project_versions")
def test_recommend_fix_version_from_project_versions(mock_versions):
    mock_versions.return_value = [
        {"name": "Release 1.0", "released": True, "releaseDate": "2025-01-01", "archived": False},
        {"name": "Release 2.0", "released": False, "releaseDate": "2026-06-01", "archived": False},
    ]
    ticket = {"key": "PROJ-1", "fix_version": "", "jira_priority": "High"}
    assert recommend_fix_version(ticket) == "Release 2.0"


@patch("agents.grooming.list_project_versions")
def test_recommend_fix_version_from_description_hint(mock_versions):
    mock_versions.return_value = [
        {"name": "Release 1.0", "released": False, "releaseDate": "2026-01-01", "archived": False},
        {"name": "Release 2.0", "released": False, "releaseDate": "2026-06-01", "archived": False},
    ]
    ticket = {
        "key": "PROJ-2",
        "title": "Ship fix in Release 1.0",
        "description": "Target release 1.0 for this bug.",
        "fix_version": "",
    }
    assert recommend_fix_version(ticket) == "Release 1.0"


def test_generate_creator_questions_flags_missing_sections():
    ticket = {
        "title": "Bug",
        "description": "",
        "acceptance_criteria": "",
        "fix_version": "",
    }
    questions = generate_creator_questions(ticket)
    assert any("description" in q.lower() for q in questions)
    assert any("acceptance criteria" in q.lower() for q in questions)
    assert any("fix version" in q.lower() for q in questions)


def test_groom_ticket_populates_assessment_fields():
    ticket = {
        "key": "PROJ-99",
        "title": "Fix css spacing on settings page",
        "description": "The padding on the settings form is inconsistent.",
        "acceptance_criteria": "",
        "fix_version": "",
        "jira_priority": "Medium",
    }
    with patch("agents.grooming.list_project_versions", return_value=[]):
        groomed = groom_ticket(ticket)

    assert groomed["board_lane"] == "pre_assessed"
    assert groomed["recommended_t_shirt_size"] in ("XS", "S", "M", "L", "XL")
    assert groomed["recommended_t_shirt_size_reason"]
    assert "settings" in groomed["recommended_t_shirt_size_reason"].lower() or "css" in groomed["recommended_t_shirt_size_reason"].lower()

    questions = json.loads(groomed["creator_questions_json"])
    assert isinstance(questions, list)
    assert len(questions) >= 1
