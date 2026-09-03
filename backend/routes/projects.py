"""REST routes for project CRUD."""

import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import config
from models.model_catalog import validate_model_choice
import database as db
from agents.jira_runner import ingest_tickets
from utils.github_push import push_project
from utils.git_worktree import remove_worktree

router = APIRouter(prefix="/api/projects", tags=["projects"])

DELETABLE_STATUSES = frozenset({"pending", "ready", "running", "error", "done"})


class TicketInput(BaseModel):
    jira_url: Optional[str] = None
    ticket_key: Optional[str] = None
    manual: Optional[dict] = None  # { title, description, acceptance_criteria }


class CreateProjectRequest(BaseModel):
    name: str
    brief: str = ""
    provider: str = "openai"   # openai | anthropic | ollama
    model: Optional[str] = None
    mode: str = "greenfield"   # greenfield | jira
    repo_context_path: Optional[str] = None
    tickets: Optional[List[TicketInput]] = None


class UpdateProjectRequest(BaseModel):
    provider: Optional[str] = None   # openai | anthropic | ollama
    model: Optional[str] = None


@router.get("")
def list_projects():
    return {"projects": db.list_projects()}


@router.post("")
def create_project(req: CreateProjectRequest):
    project_id = str(uuid.uuid4())[:8]
    model = req.model or {
        "openai":    config.OPENAI_MODEL,
        "anthropic": config.ANTHROPIC_MODEL,
        "ollama":    config.OLLAMA_MODEL,
    }.get(req.provider, config.OLLAMA_MODEL)

    err = validate_model_choice(req.provider, model)
    if err:
        raise HTTPException(status_code=400, detail=err)

    if req.mode == "jira" and req.provider == "ollama" and not req.model:
        model = config.SENIOR_DEV_MODEL or model

    repo_path = req.repo_context_path or config.REPO_CONTEXT_PATH
    if req.mode == "jira" and not repo_path:
        raise HTTPException(status_code=400, detail="repo_context_path is required for Jira mode")
    if req.mode == "jira" and not req.tickets:
        raise HTTPException(status_code=400, detail="At least one ticket is required for Jira mode")

    brief = req.brief or (f"Jira mode — {len(req.tickets or [])} ticket(s)")

    project = db.create_project(
        project_id, req.name, brief, req.provider, model,
        mode=req.mode, repo_context_path=repo_path,
    )

    if req.mode == "jira":
        db.update_project(project_id, status="ready")
        try:
            ingest_tickets(project_id, [t.model_dump() for t in req.tickets])
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    return db.get_project(project_id)


@router.get("/{project_id}")
def get_project(project_id: str):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/{project_id}")
def delete_project(project_id: str):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["status"] not in DELETABLE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete a {project['status']} session.",
        )

    worktrees = []
    if project.get("mode") == "jira":
        repo_path = project.get("repo_context_path")
        for ticket in db.list_tickets(project_id):
            wt = ticket.get("worktree_path")
            if wt:
                worktrees.append((wt, repo_path))

    if not db.delete_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")

    for wt, repo_path in worktrees:
        try:
            remove_worktree(wt, repo_path)
        except Exception:
            pass

    return {"deleted": project_id}


@router.patch("/{project_id}")
def update_project(project_id: str, req: UpdateProjectRequest):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    fields = {}
    if req.provider:
        fields["provider"] = req.provider
    if req.model is not None:
        err = validate_model_choice(req.provider or project["provider"], req.model)
        if err:
            raise HTTPException(status_code=400, detail=err)
        fields["model"] = req.model
    if fields:
        db.update_project(project_id, **fields)
    return db.get_project(project_id)


@router.get("/{project_id}/agents")
def get_agent_runs(project_id: str):
    return {"agents": db.get_agent_runs(project_id)}


@router.get("/{project_id}/artifacts")
def get_artifacts(project_id: str):
    artifacts = db.get_artifacts(project_id)
    return {"artifacts": artifacts}


@router.get("/{project_id}/tickets")
def get_tickets(project_id: str):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"tickets": db.list_tickets(project_id)}


@router.post("/{project_id}/push")
def push_to_github(project_id: str):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["status"] != "done":
        raise HTTPException(status_code=400, detail="Project pipeline must complete before pushing")
    if not config.GITHUB_TOKEN or not config.GITHUB_USERNAME:
        raise HTTPException(status_code=400, detail="GITHUB_TOKEN and GITHUB_USERNAME must be set")

    repo_name = project["name"].lower().replace(" ", "-").replace("_", "-")
    try:
        url = push_project(project_id, repo_name, project["brief"])
        return {"github_url": url, "repo": repo_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
