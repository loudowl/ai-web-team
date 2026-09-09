"""API tests for board lane validation and grooming on patch."""

import json

from fastapi.testclient import TestClient

import database as db
from main import app


def test_patch_pre_assessed_lane_sets_grooming_fields(jira_project):
    with patch_grooming_versions([]):
        ticket = db.create_ticket(
            ticket_id="t1",
            project_id="proj-test",
            title="Vague improvement",
            description="We should improve the dashboard somehow.",
            ticket_key="PROJ-50",
            board_lane="todo",
        )

    client = TestClient(app)
    resp = client.patch(
        "/api/projects/proj-test/tickets/t1",
        json={"board_lane": "pre_assessed"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["board_lane"] == "pre_assessed"
    assert body.get("recommended_t_shirt_size")
    assert body.get("recommended_t_shirt_size_reason")
    assert body.get("creator_questions_json")
    questions = json.loads(body["creator_questions_json"])
    assert isinstance(questions, list)
    assert len(questions) >= 1


def test_patch_rejects_invalid_lane(jira_project):
    db.create_ticket(
        ticket_id="t2",
        project_id="proj-test",
        title="Task",
        board_lane="todo",
    )
    client = TestClient(app)
    resp = client.patch(
        "/api/projects/proj-test/tickets/t2",
        json={"board_lane": "not_a_lane"},
    )
    assert resp.status_code == 400


class patch_grooming_versions:
    """Context manager patching Jira version lookup for grooming."""

    def __init__(self, versions):
        self.versions = versions
        self._patch = None

    def __enter__(self):
        from unittest.mock import patch

        self._patch = patch("agents.grooming.list_project_versions", return_value=self.versions)
        self._patch.start()
        return self

    def __exit__(self, *args):
        self._patch.stop()
