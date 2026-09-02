"""
Jira Mode runner — one senior_dev agent per ticket, parallel execution, milestone events.
"""

import asyncio
import json
import re
import uuid
from typing import Callable, Awaitable, List, Dict

import database as db
import config
from models.providers import stream_response
from models.providers import ollama_list_models
from models.coding_agents import pick_best_installed
from agents.prompts import (
    SENIOR_DEV_SYSTEM,
    JIRA_MILESTONES,
    jira_analyze_prompt,
    jira_implement_prompt,
)
from utils.repo_context import build_repo_context, list_repos
from utils.git_worktree import ensure_worktree
from utils.jira_client import fetch_ticket

AGENT = "senior_dev"


def _parse_task_list(markdown: str) -> List[Dict]:
    tasks = []
    for line in markdown.splitlines():
        m = re.match(r"^-\s+\[([ xX])\]\s+(.+)$", line.strip())
        if m:
            tasks.append({
                "id": str(uuid.uuid4())[:8],
                "label": m.group(2).strip(),
                "status": "done" if m.group(1).lower() == "x" else "pending",
            })
    return tasks


async def _stream_agent(
    prompt: str,
    provider: str,
    ticket_id: str,
    emit,
) -> str:
    loop = asyncio.get_event_loop()
    gen = stream_response(
        prompt=prompt,
        provider=provider,
        agent=AGENT,
        system=SENIOR_DEV_SYSTEM,
    )

    def _next_chunk():
        try:
            return next(gen)
        except StopIteration:
            return None

    full = []
    while True:
        chunk = await loop.run_in_executor(None, _next_chunk)
        if chunk is None:
            break
        full.append(chunk)
        await emit("token", AGENT, chunk, ticket_id)
    return "".join(full)


async def run_ticket(
    project: dict,
    ticket_row: dict,
    repo_context_text: str,
    repo_root: str,
    send: Callable[[str], Awaitable[None]],
):
    ticket_id = ticket_row["id"]
    provider = project["provider"]
    model = project.get("model") or ""

    async def emit(type_: str, agent: str, data: str, tid: str = None):
        payload = {"type": type_, "agent": agent, "data": data, "ticket_id": tid or ticket_id}
        await send(json.dumps(payload))

    async def milestone(milestone_id: str, status: str, detail: str = ""):
        label = next((m["label"] for m in JIRA_MILESTONES if m["id"] == milestone_id), milestone_id)
        await emit("milestone", AGENT, json.dumps({
            "milestone_id": milestone_id,
            "label": label,
            "status": status,
            "detail": detail,
        }), ticket_id)

    ticket = {
        "key": ticket_row.get("ticket_key"),
        "title": ticket_row.get("title"),
        "description": ticket_row.get("description"),
        "acceptance_criteria": ticket_row.get("acceptance_criteria"),
        "jira_url": ticket_row.get("jira_url"),
    }

    try:
        db.update_ticket(ticket_id, status="running")
        await emit("ticket_start", AGENT, f"Starting {ticket.get('key', ticket_id)}…", ticket_id)
        await emit("agent_start", AGENT, f"Senior Dev → {ticket.get('title', '')}", ticket_id)

        await milestone("fetch_ticket", "done", "Ticket loaded")
        await milestone("gather_context", "done", "Repo context gathered")

        # Worktree
        await milestone("create_worktree", "running", "Creating worktree…")
        repos = list_repos(__import__("pathlib").Path(repo_root))
        primary_repo = str(repos[0]) if repos else repo_root
        wt_path = ensure_worktree(
            primary_repo,
            project["id"],
            ticket_id,
            ticket_row.get("ticket_key"),
        )
        db.update_ticket(ticket_id, worktree_path=wt_path)
        await milestone("create_worktree", "done", wt_path)

        # Plan
        await milestone("analyze_plan", "running")
        plan_prompt = jira_analyze_prompt(ticket, repo_context_text)
        plan_output = await _stream_agent(plan_prompt, provider, ticket_id, emit)
        tasks = _parse_task_list(plan_output)
        db.update_ticket(ticket_id, tasks_json=json.dumps(tasks))
        await emit("tasks", AGENT, json.dumps(tasks), ticket_id)
        await milestone("analyze_plan", "done")

        # Implement
        await milestone("implement", "running")
        impl_prompt = jira_implement_prompt(ticket, repo_context_text, plan_output)
        impl_output = await _stream_agent(impl_prompt, provider, ticket_id, emit)
        full_output = plan_output + "\n\n---\n\n# Implementation\n\n" + impl_output

        tasks = _parse_task_list(full_output) or tasks
        db.update_ticket(
            ticket_id,
            status="done",
            output=full_output,
            tasks_json=json.dumps(tasks),
        )
        db.save_artifact(project["id"], f"{AGENT}:{ticket_id}", f"{ticket_row.get('ticket_key', ticket_id)}.md", full_output)
        await emit("tasks", AGENT, json.dumps(tasks), ticket_id)
        await milestone("implement", "done")
        await emit("agent_done", AGENT, f"Finished {ticket.get('key', ticket_id)}", ticket_id)
        await emit("ticket_done", AGENT, f"Ticket {ticket.get('key', ticket_id)} complete", ticket_id)

    except Exception as e:
        db.update_ticket(ticket_id, status="error", output=str(e))
        await emit("error", AGENT, f"❌ {ticket.get('key', ticket_id)} failed: {e}", ticket_id)
        raise


async def run_jira_pipeline(
    project_id: str,
    send: Callable[[str], Awaitable[None]],
):
    project = db.get_project(project_id)
    if not project:
        raise ValueError("Project not found")

    tickets = db.list_tickets(project_id)
    if not tickets:
        await send(json.dumps({"type": "error", "agent": "system", "data": "No tickets for this project"}))
        return

    repo_path = project.get("repo_context_path") or config.REPO_CONTEXT_PATH
    ctx = build_repo_context(repo_path)
    repo_context_text = ctx["context_text"]

    # Pick best Ollama model if provider is ollama
    if project["provider"] == "ollama":
        if project.get("model"):
            config.AGENT_MODELS["senior_dev"] = project["model"]
        else:
            best = pick_best_installed(ollama_list_models())
            if best:
                config.AGENT_MODELS["senior_dev"] = best
                db.update_project(project_id, model=best)

    db.update_project(project_id, status="running")

    async def run_one(ticket_row):
        try:
            await run_ticket(project, ticket_row, repo_context_text, ctx["root"], send)
        except Exception:
            pass  # error already emitted

    await asyncio.gather(*[run_one(t) for t in tickets])

    # Final status
    updated = db.list_tickets(project_id)
    if any(t["status"] == "error" for t in updated):
        db.update_project(project_id, status="error")
    else:
        db.update_project(project_id, status="done")

    await send(json.dumps({
        "type": "pipeline_done",
        "agent": "system",
        "data": f"Jira mode complete — {len(updated)} ticket(s) processed.",
    }))


def ingest_tickets(project_id: str, ticket_inputs: List[dict]) -> List[Dict]:
    """Create ticket rows from API/manual inputs."""
    created = []
    for raw in ticket_inputs:
        data = fetch_ticket(
            jira_url=raw.get("jira_url"),
            ticket_key=raw.get("ticket_key"),
            manual=raw.get("manual"),
        )
        tid = str(uuid.uuid4())[:8]
        row = db.create_ticket(
            ticket_id=tid,
            project_id=project_id,
            title=data["title"],
            description=data.get("description", ""),
            ticket_key=data.get("key"),
            jira_url=data.get("jira_url"),
            acceptance_criteria=data.get("acceptance_criteria", ""),
        )
        created.append(row)
    return created
