"""Tests for Jira client normalization helpers."""

from utils.jira_client import parse_project_key, parse_ticket_key


def test_parse_ticket_key_from_browse_url():
    url = "https://example.atlassian.net/browse/PROJ-123"
    assert parse_ticket_key(url) == "PROJ-123"


def test_parse_project_key_from_issue_key():
    assert parse_project_key(ticket_key="PROJ-456") == "PROJ"
    assert parse_project_key(jira_url="https://example.atlassian.net/browse/ABC-1") == "ABC"


def test_parse_project_key_invalid():
    assert parse_project_key(ticket_key="invalid") is None
