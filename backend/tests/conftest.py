"""Shared pytest fixtures — isolated SQLite DB per test."""

import os
import tempfile

import pytest

import config
import database as db


@pytest.fixture()
def temp_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr(config, "DB_PATH", path)
    db.init()
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture()
def jira_project(temp_db):
    row = db.create_project(
        project_id="proj-test",
        name="Test Jira Project",
        brief="board tests",
        provider="anthropic",
        model="claude-haiku-4-5",
        mode="jira",
    )
    db.update_project(
        "proj-test",
        jira_project_key="PROJ",
        jira_board_id="42",
    )
    return row
