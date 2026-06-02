"""REST routes for project CRUD."""

import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

import config
import database as db
from utils.github_push import push_project

router = APIRouter(prefix="/api/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str
    brief: str
    provider: str = "openai"   # openai | anthropic | ollama
    model: Optional[str] = None


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

    project = db.create_project(project_id, req.name, req.brief, req.provider, model)
    return project


@router.get("/{project_id}")
def get_project(project_id: str):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}")
def update_project(project_id: str, req: UpdateProjectRequest):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    fields = {}
    if req.provider:
        fields["provider"] = req.provider
    if req.model is not None:
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
