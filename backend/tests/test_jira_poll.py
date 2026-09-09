"""Tests for Jira poll sync and refresh behavior."""

from unittest.mock import patch

import pytest

import database as db
from services import jira_poll


SAMPLE_ISSUE_NO_FIX = {
    "key": "PROJ-100",
    "title": "Add export button",
    "description": "Users need CSV export.",
    "acceptance_criteria": "",
    "fix_version": "",
    "fix_versions": [],
    "jira_url": "https://example.atlassian.net/browse/PROJ-100",
    "jira_status": "To Do",
    "jira_priority": "Medium",
    "labels": [],
    "story_points": None,
    "project_key": "PROJ",
}

SAMPLE_ISSUE_WITH_FIX = {
    **SAMPLE_ISSUE_NO_FIX,
    "key": "PROJ-200",
    "jira_url": "https://example.atlassian.net/browse/PROJ-200",
    "fix_version": "Release 2.0",
    "fix_versions": ["Release 2.0"],
}


@pytest.mark.asyncio
async def test_sync_adds_new_tickets(jira_project):
    with patch("services.jira_poll.jira_configured", return_value=True):
        with patch(
            "services.jira_poll.fetch_board_todo_issues",
            return_value=[SAMPLE_ISSUE_NO_FIX, SAMPLE_ISSUE_WITH_FIX],
        ):
            with patch("agents.grooming.list_project_versions", return_value=[]):
                result = await jira_poll.sync_project_from_jira("proj-test")

    assert result["found"] == 2
    assert len(result["added"]) == 2
    assert len(result["updated"]) == 0

    rows = db.list_tickets("proj-test")
    by_key = {r["ticket_key"]: r for r in rows}
    assert by_key["PROJ-100"]["board_lane"] == "pre_assessed"
    assert by_key["PROJ-200"]["board_lane"] == "todo"
    assert by_key["PROJ-200"]["fix_version"] == "Release 2.0"


@pytest.mark.asyncio
async def test_sync_refreshes_existing_ticket_lane(jira_project):
    with patch("agents.grooming.list_project_versions", return_value=[]):
        jira_poll._ingest_polled_issue("proj-test", SAMPLE_ISSUE_NO_FIX)
    existing = db.find_ticket_by_key("proj-test", "PROJ-100")
    assert existing["board_lane"] == "pre_assessed"

    updated_issue = {
        **SAMPLE_ISSUE_NO_FIX,
        "fix_version": "Release 2.0",
        "fix_versions": ["Release 2.0"],
    }
    with patch("services.jira_poll.jira_configured", return_value=True):
        with patch("services.jira_poll.fetch_board_todo_issues", return_value=[updated_issue]):
            with patch("agents.grooming.list_project_versions", return_value=[]):
                result = await jira_poll.sync_project_from_jira("proj-test")

    assert len(result["added"]) == 0
    assert len(result["updated"]) == 1
    row = db.get_ticket(existing["id"])
    assert row["fix_version"] == "Release 2.0"
    assert row["board_lane"] == "todo"


@pytest.mark.asyncio
async def test_reset_board_clears_and_reimports(jira_project):
    with patch("agents.grooming.list_project_versions", return_value=[]):
        jira_poll._ingest_polled_issue("proj-test", SAMPLE_ISSUE_NO_FIX)
    assert len(db.list_tickets("proj-test")) == 1

    with patch("services.jira_poll.jira_configured", return_value=True):
        with patch("services.jira_poll.fetch_board_todo_issues", return_value=[SAMPLE_ISSUE_WITH_FIX]):
            with patch("agents.grooming.list_project_versions", return_value=[]):
                result = await jira_poll.reset_board_from_jira("proj-test")

    assert result["reset"] is True
    assert result["deleted"] == 1
    assert len(result["added"]) == 1
    rows = db.list_tickets("proj-test")
    assert len(rows) == 1
    assert rows[0]["ticket_key"] == "PROJ-200"
