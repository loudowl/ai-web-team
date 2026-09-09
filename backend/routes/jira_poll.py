"""Jira board polling — sync To Do issues into local swim board."""

from typing import Optional

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import database as db
from services import jira_poll
from utils.jira_client import jira_configured, list_agile_boards

router = APIRouter(prefix="/api/jira-poll", tags=["jira-poll"])


class PollConfigRequest(BaseModel):
    board_id: Optional[str] = None
    project_key: Optional[str] = None
    jql: Optional[str] = None
    interval_sec: Optional[int] = Field(None, ge=30, le=3600)
    no_local_models: Optional[bool] = None
    reassign_all_projects: Optional[bool] = False


@router.get("/boards")
def get_boards(project_key: Optional[str] = None):
    if not jira_configured():
        raise HTTPException(status_code=400, detail="Jira API is not configured")
    try:
        return {"boards": list_agile_boards(project_key_or_id=project_key)}
    except requests.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        raise HTTPException(
            status_code=502,
            detail=f"Jira board list failed: {detail[:500]}",
        ) from exc
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Jira board list failed: {exc}") from exc


@router.get("/projects/{project_id}/status")
def get_poll_status(project_id: str):
    try:
        return jira_poll.poll_status(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/projects/{project_id}/sync")
async def sync_now(project_id: str, req: PollConfigRequest = PollConfigRequest()):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.get("mode") != "jira":
        raise HTTPException(status_code=400, detail="Not a Jira-mode project")
    if req.project_key:
        db.update_project(project_id, jira_project_key=req.project_key)
    try:
        result = await jira_poll.sync_project_from_jira(
            project_id,
            board_id=req.board_id,
            jql=req.jql,
            no_local_models=req.no_local_models,
        )
        if req.no_local_models:
            result["reassign"] = jira_poll.reassign_todo_models(
                project_id=project_id,
                all_projects=bool(req.reassign_all_projects),
                exclude_local=True,
            )
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except requests.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        raise HTTPException(status_code=502, detail=f"Jira sync failed: {detail[:500]}") from exc
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Jira sync failed: {exc}") from exc


@router.post("/projects/{project_id}/start")
async def start_poll(project_id: str, req: PollConfigRequest = PollConfigRequest()):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.get("mode") != "jira":
        raise HTTPException(status_code=400, detail="Not a Jira-mode project")
    if req.project_key:
        db.update_project(project_id, jira_project_key=req.project_key)
    try:
        return await jira_poll.start_poll(
            project_id,
            board_id=req.board_id,
            jql=req.jql,
            interval_sec=req.interval_sec,
            no_local_models=req.no_local_models,
            reassign_all_projects=bool(req.reassign_all_projects),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except requests.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        raise HTTPException(status_code=502, detail=f"Jira poll failed: {detail[:500]}") from exc
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Jira poll failed: {exc}") from exc


@router.post("/projects/{project_id}/reset")
async def reset_board(project_id: str, req: PollConfigRequest = PollConfigRequest()):
    """Delete all local board tickets and re-import from Jira To Do."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.get("mode") != "jira":
        raise HTTPException(status_code=400, detail="Not a Jira-mode project")
    if req.project_key:
        db.update_project(project_id, jira_project_key=req.project_key)
    try:
        result = await jira_poll.reset_board_from_jira(
            project_id,
            board_id=req.board_id,
            jql=req.jql,
            no_local_models=req.no_local_models,
        )
        if req.no_local_models:
            result["reassign"] = jira_poll.reassign_todo_models(
                project_id=project_id,
                all_projects=bool(req.reassign_all_projects),
                exclude_local=True,
            )
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except requests.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        raise HTTPException(status_code=502, detail=f"Jira reset failed: {detail[:500]}") from exc
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Jira reset failed: {exc}") from exc


@router.post("/projects/{project_id}/stop")
async def stop_poll(project_id: str):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return await jira_poll.stop_poll(project_id)


@router.post("/projects/{project_id}/reassign-models")
def reassign_models(project_id: str, req: PollConfigRequest = PollConfigRequest()):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.get("mode") != "jira":
        raise HTTPException(status_code=400, detail="Not a Jira-mode project")
    if req.no_local_models is not None:
        db.update_project(project_id, jira_no_local_models=1 if req.no_local_models else 0)
    try:
        exclude = req.no_local_models if req.no_local_models is not None else bool(project.get("jira_no_local_models"))
        if not exclude:
            return {
                "no_local_models": False,
                "reassigned": [],
                "reassigned_count": 0,
                "skipped": [],
                "message": "Enable no local models to reassign Ollama tickets to cloud providers.",
            }
        return jira_poll.reassign_todo_models(
            project_id=project_id,
            all_projects=bool(req.reassign_all_projects),
            exclude_local=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
