"""Board API — swim lanes, per-ticket launch, archive."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import database as db
from agents.jira_runner import ingest_tickets, run_single_ticket
from models.model_catalog import validate_model_choice
from models.providers import resolve_ollama_model, ollama_missing_info
from utils.jira_client import parse_project_key
from routes.ws_hub import is_ticket_running, schedule_ticket_run

router = APIRouter(prefix="/api/projects", tags=["board"])

VALID_LANES = frozenset({"pre_assessed", "todo", "in_progress", "in_review", "dev_complete"})
VALID_WORKFLOWS = frozenset({"simple", "fix", "full_cycle"})


class AddTicketRequest(BaseModel):
    jira_url: Optional[str] = None
    ticket_key: Optional[str] = None
    manual: Optional[dict] = None


class UpdateTicketBoardRequest(BaseModel):
    board_lane: Optional[str] = None
    archive: Optional[bool] = None
    fix_version: Optional[str] = None
    t_shirt_size: Optional[str] = None
    assigned_provider: Optional[str] = None
    assigned_model: Optional[str] = None
    recommended_fix_version: Optional[str] = None
    recommended_t_shirt_size: Optional[str] = None
    jira_priority: Optional[str] = None


class RunTicketRequest(BaseModel):
    workflow: str = "simple"


@router.post("/{project_id}/tickets")
def add_ticket(project_id: str, req: AddTicketRequest):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.get("mode") != "jira":
        raise HTTPException(status_code=400, detail="Board is only available in Jira mode")

    created = ingest_tickets(project_id, [req.model_dump()])
    row = created[0]
    if not row.get("board_lane"):
        db.update_ticket(row["id"], board_lane="todo")
    return db.get_ticket(row["id"])


@router.patch("/{project_id}/tickets/{ticket_id}")
def update_ticket_board(project_id: str, ticket_id: str, req: UpdateTicketBoardRequest):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    ticket = db.get_ticket(ticket_id)
    if not ticket or ticket["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Ticket not found")

    fields = {}
    if req.board_lane is not None:
        lane = req.board_lane
        if lane == "pre_groomed":
            lane = "pre_assessed"
        if lane not in VALID_LANES:
            raise HTTPException(status_code=400, detail=f"Invalid lane: {req.board_lane}")
        fields["board_lane"] = lane
        if lane == "pre_assessed":
            from agents.grooming import groom_ticket

            groomed = groom_ticket(
                {
                    "key": ticket.get("ticket_key") or "",
                    "project_key": parse_project_key(ticket.get("ticket_key")),
                    "fix_version": ticket.get("fix_version") or "",
                    "t_shirt_size": ticket.get("t_shirt_size") or "",
                    "jira_priority": ticket.get("jira_priority") or "",
                    "title": ticket.get("title") or "",
                    "description": ticket.get("description") or "",
                    "acceptance_criteria": ticket.get("acceptance_criteria") or "",
                    "story_points": ticket.get("complexity_score"),
                },
                tier=ticket.get("complexity_tier"),
                score=ticket.get("complexity_score"),
            )
            if not (ticket.get("t_shirt_size") or "").strip():
                fields["recommended_t_shirt_size"] = groomed.get("recommended_t_shirt_size")
                fields["recommended_t_shirt_size_reason"] = groomed.get("recommended_t_shirt_size_reason")
                fields["creator_questions_json"] = groomed.get("creator_questions_json")
            if not (ticket.get("fix_version") or "").strip():
                fields["recommended_fix_version"] = groomed.get("recommended_fix_version")
            if not (ticket.get("jira_priority") or "").strip() and groomed.get("jira_priority"):
                fields["jira_priority"] = groomed.get("jira_priority")
    if req.fix_version is not None:
        fields["fix_version"] = req.fix_version.strip() or None
        if req.fix_version.strip():
            fields["recommended_fix_version"] = None
    if req.t_shirt_size is not None:
        fields["t_shirt_size"] = req.t_shirt_size.strip().upper() or None
        if req.t_shirt_size.strip():
            fields["recommended_t_shirt_size"] = None
            fields["recommended_t_shirt_size_reason"] = None
    if req.recommended_fix_version is not None:
        fields["recommended_fix_version"] = req.recommended_fix_version.strip() or None
    if req.recommended_t_shirt_size is not None:
        fields["recommended_t_shirt_size"] = req.recommended_t_shirt_size.strip().upper() or None
    if req.jira_priority is not None:
        fields["jira_priority"] = req.jira_priority.strip() or None
    if req.assigned_provider is not None:
        fields["assigned_provider"] = req.assigned_provider
    if req.assigned_model is not None:
        err = validate_model_choice(req.assigned_provider or ticket.get("assigned_provider") or project["provider"], req.assigned_model)
        if err:
            raise HTTPException(status_code=400, detail=err)
        fields["assigned_model"] = req.assigned_model
    if req.archive:
        from datetime import datetime
        fields["archived_at"] = datetime.utcnow().isoformat()
        fields["board_lane"] = "archived"

    if fields:
        db.update_ticket(ticket_id, **fields)
    return db.get_ticket(ticket_id)


@router.post("/{project_id}/tickets/{ticket_id}/run")
async def run_ticket(project_id: str, ticket_id: str, req: RunTicketRequest):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.get("mode") != "jira":
        raise HTTPException(status_code=400, detail="Ticket runs are only available in Jira mode")

    ticket = db.get_ticket(ticket_id)
    if not ticket or ticket["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.get("archived_at"):
        raise HTTPException(status_code=400, detail="Cannot run an archived ticket")

    workflow = req.workflow if req.workflow in VALID_WORKFLOWS else "simple"
    if is_ticket_running(project_id, ticket_id):
        raise HTTPException(status_code=409, detail="Ticket is already running")

    if project.get("provider") == "ollama":
        try:
            resolve_ollama_model(project.get("model") or None, allow_fallback=not bool(project.get("model")))
        except RuntimeError:
            raise HTTPException(
                status_code=409,
                detail=ollama_missing_info(project.get("model") or ""),
            ) from None

    db.update_ticket(ticket_id, workflow=workflow)
    if project["status"] == "pending":
        db.update_project(project_id, status="ready")

    schedule_ticket_run(project_id, ticket_id, workflow, run_single_ticket)
    return {"started": ticket_id, "workflow": workflow}


@router.get("/{project_id}/tickets/archived")
def list_archived(project_id: str):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"tickets": db.list_archived_tickets(project_id)}


@router.get("/archived/tickets")
def list_all_archived(limit: int = 100):
    return {"tickets": db.list_archived_tickets(limit=limit)}
