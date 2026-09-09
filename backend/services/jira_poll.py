"""Background Jira To Do polling and ticket ingest with model assignment."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Optional

import config
import database as db
from agents.complexity import score_ticket
from agents.grooming import groom_ticket
from agents.model_router import assign_model
from utils.jira_client import fetch_board_todo_issues, jira_configured, resolve_default_board_id


_poll_tasks: Dict[str, asyncio.Task] = {}


def _project_poll_key(project_id: str) -> str:
    return project_id


def _project_exclude_local(project: dict) -> bool:
    return bool(project.get("jira_no_local_models"))


def _ticket_issue_payload(ticket: dict) -> dict:
    return {
        "title": ticket.get("title") or "",
        "description": ticket.get("description") or "",
        "acceptance_criteria": ticket.get("acceptance_criteria") or "",
        "labels": [],
    }


def reassign_todo_models(
    *,
    project_id: str = None,
    all_projects: bool = False,
    exclude_local: bool = True,
) -> Dict:
    """
    Re-score and re-assign models for To Do lane tickets.

    When exclude_local is True, tickets currently on Ollama are moved to cloud providers.
    """
    if all_projects:
        projects = [p for p in db.list_projects(limit=100) if p.get("mode") == "jira"]
    elif project_id:
        project = db.get_project(project_id)
        if not project:
            raise ValueError("Project not found")
        projects = [project]
    else:
        raise ValueError("project_id is required unless all_projects is true")

    reassigned = []
    skipped = []

    for project in projects:
        exclude = exclude_local if exclude_local is not None else _project_exclude_local(project)
        for ticket in db.list_tickets(project["id"]):
            if ticket.get("archived_at"):
                continue
            lane = ticket.get("board_lane") or "todo"
            if lane != "todo":
                continue
            if ticket.get("status") == "running":
                skipped.append({"ticket_key": ticket.get("ticket_key"), "reason": "running"})
                continue

            current_provider = (ticket.get("assigned_provider") or "").lower()
            if exclude and current_provider != "ollama":
                skipped.append({"ticket_key": ticket.get("ticket_key"), "reason": "already_cloud"})
                continue

            tier = ticket.get("complexity_tier")
            score = ticket.get("complexity_score")
            if not tier:
                tier, score = score_ticket(_ticket_issue_payload(ticket))

            routing = assign_model(tier, exclude_local=exclude)
            if (
                current_provider == routing["provider"]
                and ticket.get("assigned_model") == routing["model"]
            ):
                skipped.append({"ticket_key": ticket.get("ticket_key"), "reason": "unchanged"})
                continue

            db.update_ticket(
                ticket["id"],
                assigned_provider=routing["provider"],
                assigned_model=routing["model"],
                complexity_tier=tier,
                complexity_score=score,
            )
            reassigned.append({
                "ticket_key": ticket.get("ticket_key"),
                "ticket_id": ticket["id"],
                "project_id": project["id"],
                "from_provider": current_provider or None,
                "assigned_provider": routing["provider"],
                "assigned_model": routing["model"],
                "complexity_tier": tier,
            })

    return {
        "exclude_local": exclude_local,
        "reassigned": reassigned,
        "reassigned_count": len(reassigned),
        "skipped": skipped,
    }


async def reset_board_from_jira(
    project_id: str,
    *,
    board_id: str = None,
    jql: str = None,
    max_results: int = 50,
    no_local_models: bool = None,
) -> Dict:
    """Clear the local board and re-import To Do issues from Jira (Pre assessed lane)."""
    project = db.get_project(project_id)
    if not project:
        raise ValueError("Project not found")
    if project.get("mode") != "jira":
        raise ValueError("Jira poll is only available for Jira-mode projects")

    from routes.ws_hub import is_ticket_running

    for ticket in db.list_tickets(project_id, include_archived=True):
        if ticket.get("status") == "running" or is_ticket_running(project_id, ticket["id"]):
            raise RuntimeError(
                f"Cannot reset board while {ticket.get('ticket_key') or ticket['id']} is running"
            )

    deleted = db.delete_all_project_tickets(project_id)
    sync_result = await sync_project_from_jira(
        project_id,
        board_id=board_id,
        jql=jql,
        max_results=max_results,
        no_local_models=no_local_models,
    )
    sync_result["deleted"] = deleted
    sync_result["reset"] = True
    return sync_result


async def sync_project_from_jira(
    project_id: str,
    *,
    board_id: str = None,
    jql: str = None,
    max_results: int = 50,
    no_local_models: bool = None,
) -> Dict:
    """One-shot poll: fetch To Do issues and ingest new tickets."""
    project = db.get_project(project_id)
    if not project:
        raise ValueError("Project not found")
    if project.get("mode") != "jira":
        raise ValueError("Jira poll is only available for Jira-mode projects")
    if not jira_configured():
        raise RuntimeError("Jira API is not configured")

    if no_local_models is not None:
        db.update_project(project_id, jira_no_local_models=1 if no_local_models else 0)
        project = db.get_project(project_id)

    exclude_local = (
        no_local_models if no_local_models is not None else _project_exclude_local(project)
    )

    effective_board = board_id or project.get("jira_board_id") or config.JIRA_BOARD_ID or None
    effective_jql = jql or project.get("jira_todo_jql") or None
    project_key = project.get("jira_project_key") or config.JIRA_PROJECT_KEY or None
    if not effective_board and project_key:
        effective_board = resolve_default_board_id(project_key)

    issues = fetch_board_todo_issues(
        board_id=effective_board,
        project_key=project_key,
        jql=effective_jql,
        max_results=max_results,
    )

    added = []
    updated = []
    skipped = []
    errors = []

    for issue in issues:
        key = issue.get("key")
        if not key:
            continue
        existing = db.find_ticket_by_key(project_id, key)
        if existing:
            try:
                row = _refresh_polled_issue(existing, issue, exclude_local=exclude_local)
                updated.append({
                    "ticket_key": key,
                    "ticket_id": row["id"],
                    "board_lane": row.get("board_lane"),
                    "fix_version": row.get("fix_version"),
                })
            except Exception as exc:
                errors.append({"ticket_key": key, "error": str(exc)})
            continue
        try:
            row = _ingest_polled_issue(project_id, issue, exclude_local=exclude_local)
            added.append({
                "ticket_key": key,
                "ticket_id": row["id"],
                "complexity_tier": row.get("complexity_tier"),
                "assigned_provider": row.get("assigned_provider"),
                "assigned_model": row.get("assigned_model"),
            })
        except Exception as exc:
            errors.append({"ticket_key": key, "error": str(exc)})

    now = datetime.utcnow().isoformat()
    db.update_project(project_id, jira_last_poll_at=now)
    if board_id:
        db.update_project(project_id, jira_board_id=board_id)
    if jql:
        db.update_project(project_id, jira_todo_jql=jql)

    return {
        "project_id": project_id,
        "polled_at": now,
        "found": len(issues),
        "added": added,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
        "no_local_models": exclude_local,
    }


_ACTIVE_LANES = frozenset({"in_progress", "in_review", "dev_complete"})


def _refresh_polled_issue(ticket_row: Dict, issue: Dict, *, exclude_local: bool = False) -> Dict:
    """Update an existing local ticket from latest Jira fields."""
    tier, score = score_ticket(issue)
    groomed = groom_ticket(issue, tier=tier, score=score)

    fields = {
        "title": issue.get("title") or ticket_row.get("title"),
        "description": issue.get("description") or "",
        "acceptance_criteria": issue.get("acceptance_criteria") or "",
        "fix_version": groomed.get("fix_version"),
        "jira_status": issue.get("jira_status") or "",
        "jira_priority": groomed.get("jira_priority"),
        "t_shirt_size": groomed.get("t_shirt_size"),
        "recommended_t_shirt_size": groomed.get("recommended_t_shirt_size"),
        "recommended_t_shirt_size_reason": groomed.get("recommended_t_shirt_size_reason"),
        "creator_questions_json": groomed.get("creator_questions_json"),
        "recommended_fix_version": groomed.get("recommended_fix_version"),
        "complexity_tier": groomed["complexity_tier"],
        "complexity_score": groomed["complexity_score"],
    }

    if groomed.get("fix_version"):
        fields["recommended_fix_version"] = None

    current_lane = ticket_row.get("board_lane") or "todo"
    if ticket_row.get("status") != "running" and current_lane not in _ACTIVE_LANES:
        fields["board_lane"] = groomed["board_lane"]

    db.update_ticket(ticket_row["id"], **fields)
    return db.get_ticket(ticket_row["id"])


def _ingest_polled_issue(project_id: str, issue: Dict, *, exclude_local: bool = False) -> Dict:
    tier, score = score_ticket(issue)
    routing = assign_model(tier, exclude_local=exclude_local)
    groomed = groom_ticket(issue, tier=tier, score=score)
    tid = str(uuid.uuid4())[:8]
    return db.create_ticket(
        ticket_id=tid,
        project_id=project_id,
        title=issue.get("title") or issue.get("key") or "Untitled",
        description=issue.get("description") or "",
        ticket_key=issue.get("key"),
        jira_url=issue.get("jira_url"),
        acceptance_criteria=issue.get("acceptance_criteria") or "",
        board_lane=groomed["board_lane"],
        fix_version=groomed.get("fix_version"),
        assigned_provider=routing["provider"],
        assigned_model=routing["model"],
        complexity_tier=groomed["complexity_tier"],
        complexity_score=groomed["complexity_score"],
        jira_status=issue.get("jira_status") or "",
        ingest_source="poll",
        jira_priority=groomed.get("jira_priority"),
        t_shirt_size=groomed.get("t_shirt_size"),
        recommended_t_shirt_size=groomed.get("recommended_t_shirt_size"),
        recommended_t_shirt_size_reason=groomed.get("recommended_t_shirt_size_reason"),
        creator_questions_json=groomed.get("creator_questions_json"),
        recommended_fix_version=groomed.get("recommended_fix_version"),
    )


async def _poll_loop(project_id: str, interval_sec: int):
    while True:
        try:
            await sync_project_from_jira(project_id)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"[jira-poll] project {project_id} sync failed: {exc}")
        await asyncio.sleep(interval_sec)


async def start_poll(
    project_id: str,
    *,
    board_id: str = None,
    jql: str = None,
    interval_sec: int = None,
    no_local_models: bool = None,
    reassign_all_projects: bool = False,
) -> Dict:
    project = db.get_project(project_id)
    if not project:
        raise ValueError("Project not found")

    interval = interval_sec or project.get("jira_poll_interval_sec") or 300
    interval = max(30, int(interval))

    await stop_poll(project_id)

    updates = {"jira_poll_active": 1, "jira_poll_interval_sec": interval}
    if board_id:
        updates["jira_board_id"] = board_id
    if jql:
        updates["jira_todo_jql"] = jql
    if no_local_models is not None:
        updates["jira_no_local_models"] = 1 if no_local_models else 0
    db.update_project(project_id, **updates)

    initial = await sync_project_from_jira(
        project_id,
        board_id=board_id,
        jql=jql,
        no_local_models=no_local_models,
    )

    reassign_result = None
    if no_local_models:
        reassign_result = reassign_todo_models(
            project_id=project_id,
            all_projects=reassign_all_projects,
            exclude_local=True,
        )

    task = asyncio.create_task(_poll_loop(project_id, interval))
    _poll_tasks[_project_poll_key(project_id)] = task

    return {
        "started": True,
        "project_id": project_id,
        "interval_sec": interval,
        "initial_sync": initial,
        "reassign": reassign_result,
        "no_local_models": bool(no_local_models),
    }


async def stop_poll(project_id: str) -> Dict:
    key = _project_poll_key(project_id)
    task = _poll_tasks.pop(key, None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    db.update_project(project_id, jira_poll_active=0)
    return {"stopped": True, "project_id": project_id}


def poll_status(project_id: str) -> Dict:
    project = db.get_project(project_id)
    if not project:
        raise ValueError("Project not found")
    key = _project_poll_key(project_id)
    running = key in _poll_tasks and not _poll_tasks[key].done()
    return {
        "project_id": project_id,
        "active": bool(project.get("jira_poll_active")) and running,
        "configured": jira_configured(),
        "board_id": project.get("jira_board_id") or config.JIRA_BOARD_ID,
        "project_key": project.get("jira_project_key") or config.JIRA_PROJECT_KEY,
        "jql": project.get("jira_todo_jql"),
        "interval_sec": project.get("jira_poll_interval_sec"),
        "last_poll_at": project.get("jira_last_poll_at"),
        "no_local_models": bool(project.get("jira_no_local_models")),
    }


async def resume_active_polls():
    """Re-start polling loops for projects marked active (server restart)."""
    for project in db.list_projects(limit=100):
        if project.get("mode") != "jira":
            continue
        if not project.get("jira_poll_active"):
            continue
        try:
            await start_poll(
                project["id"],
                board_id=project.get("jira_board_id"),
                jql=project.get("jira_todo_jql"),
                interval_sec=project.get("jira_poll_interval_sec") or 300,
            )
        except Exception as exc:
            print(f"[jira-poll] failed to resume {project['id']}: {exc}")
