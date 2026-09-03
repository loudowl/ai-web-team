"""Global Jira board — all active tickets across batches."""

from fastapi import APIRouter, HTTPException

import database as db

router = APIRouter(prefix="/api/board", tags=["board"])


@router.get("/tickets")
def list_global_board_tickets():
    """Return every non-archived ticket on Jira-mode project boards."""
    tickets = db.list_all_board_tickets()
    projects = [p for p in db.list_projects(limit=50) if p.get("mode") == "jira"]
    return {"tickets": tickets, "project_count": len(projects)}


@router.get("/default-project")
def default_jira_project():
    project = db.get_latest_jira_project()
    if not project:
        raise HTTPException(status_code=404, detail="No Jira board batch yet — create one first.")
    return project
