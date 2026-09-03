"""
Jira Mode runner — one senior_dev agent per ticket (concurrency capped via JIRA_MAX_PARALLEL).
"""

import asyncio
import contextlib
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
    jira_implement_retry_prompt,
)
from utils.repo_context import build_repo_context, list_repos
from utils.git_worktree import ensure_worktree
from utils.jira_client import fetch_ticket
from utils.patch_apply import apply_patches, parse_code_blocks
from utils.github_pr import publish_ticket_changes

AGENT = "senior_dev"


def _validate_plan(plan_output: str, ticket: dict) -> None:
    """Fail fast when the model clearly ignored the Jira ticket."""
    text = plan_output.lower()
    key = (ticket.get("key") or "").lower()
    if not key or key not in text:
        raise RuntimeError(
            f"Plan does not reference ticket {ticket.get('key', '')}. "
            "The model likely lost context — delete this session and retry."
        )

    title = ticket.get("title") or ""
    stop = {
        "reduce", "article", "articles", "pages", "page", "frontend", "backend",
        "implement", "fixed", "fixes", "update", "updates", "change", "changes",
        "ticket", "jira", "issue", "task", "fe", "seo", "the", "and", "for", "with",
    }
    keywords = [
        w.lower() for w in re.findall(r"[A-Za-z]{3,}", title)
        if w.lower() not in stop
    ][:8]
    hits = sum(1 for w in keywords if w in text)
    if hits < 2:
        raise RuntimeError(
            f"Plan does not address the ticket topic ({title}). "
            f"Expected terms like: {', '.join(keywords[:5])}. "
            "The model likely lost context — delete this session and retry."
        )


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
    phase: str = "llm",
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

    await emit("thinking", AGENT, json.dumps({
        "phase": phase,
        "message": "Waiting for model — local Ollama can take several minutes before the first token.",
    }), ticket_id)

    full = []
    got_token = False
    pulsing = True

    async def _heartbeat():
        while pulsing:
            await asyncio.sleep(20)
            if pulsing and not got_token:
                await emit("thinking", AGENT, json.dumps({
                    "phase": phase,
                    "message": "Still thinking…",
                }), ticket_id)

    heartbeat = asyncio.create_task(_heartbeat())
    try:
        while True:
            chunk = await loop.run_in_executor(None, _next_chunk)
            if chunk is None:
                break
            if not got_token:
                got_token = True
            full.append(chunk)
            await emit("token", AGENT, chunk, ticket_id)
    finally:
        pulsing = False
        heartbeat.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await heartbeat

    return "".join(full)


async def run_ticket(
    project: dict,
    ticket_row: dict,
    send: Callable[[str], Awaitable[None]],
):
    ticket_id = ticket_row["id"]
    provider = project["provider"]

    ticket = {
        "key": ticket_row.get("ticket_key"),
        "title": ticket_row.get("title"),
        "description": ticket_row.get("description"),
        "acceptance_criteria": ticket_row.get("acceptance_criteria"),
        "jira_url": ticket_row.get("jira_url"),
    }

    repo_path = project.get("repo_context_path") or config.REPO_CONTEXT_PATH
    ctx = build_repo_context(repo_path, ticket=ticket)
    analyze_repo_text = ctx["analyze_repo_text"]
    repo_root = ctx["root"]

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

    try:
        db.update_ticket(ticket_id, status="running", output="")
        await emit("ticket_start", AGENT, f"Starting {ticket.get('key', ticket_id)}…", ticket_id)
        await emit("agent_start", AGENT, f"Senior Dev → {ticket.get('title', '')}", ticket_id)

        await milestone("fetch_ticket", "done", "Ticket loaded")
        await milestone("gather_context", "done", "Repo context gathered")

        # Worktree
        await milestone("create_worktree", "running", "Creating worktree…")
        repos = list_repos(__import__("pathlib").Path(repo_root).resolve())
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
        plan_prompt = jira_analyze_prompt(ticket, analyze_repo_text)
        plan_output = await _stream_agent(plan_prompt, provider, ticket_id, emit, phase="analyze_plan")
        db.update_ticket(ticket_id, output=plan_output)
        _validate_plan(plan_output, ticket)
        tasks = _parse_task_list(plan_output)
        db.update_ticket(ticket_id, tasks_json=json.dumps(tasks))
        await emit("tasks", AGENT, json.dumps(tasks), ticket_id)
        await milestone("analyze_plan", "done")

        # Implement
        await milestone("implement", "running")
        impl_prompt = jira_implement_prompt(ticket, ctx["repo_text"], plan_output)
        impl_output = await _stream_agent(impl_prompt, provider, ticket_id, emit, phase="implement")
        full_output = plan_output + "\n\n---\n\n# Implementation\n\n" + impl_output

        patches = parse_code_blocks(impl_output) or parse_code_blocks(full_output)
        if not patches:
            await emit("thinking", AGENT, json.dumps({
                "phase": "implement",
                "message": "No code blocks found — retrying with stricter format instructions…",
            }), ticket_id)
            retry_prompt = jira_implement_retry_prompt(ticket, plan_output)
            retry_output = await _stream_agent(
                retry_prompt, provider, ticket_id, emit, phase="implement",
            )
            impl_output = impl_output + "\n\n---\n\n# Retry (code files)\n\n" + retry_output
            full_output = plan_output + "\n\n---\n\n# Implementation\n\n" + impl_output
            patches = parse_code_blocks(retry_output) or parse_code_blocks(impl_output) or parse_code_blocks(full_output)

        tasks = _parse_task_list(full_output) or tasks
        db.update_ticket(ticket_id, output=full_output, tasks_json=json.dumps(tasks))
        db.save_artifact(project["id"], f"{AGENT}:{ticket_id}", f"{ticket_row.get('ticket_key', ticket_id)}.md", full_output)
        await emit("tasks", AGENT, json.dumps(tasks), ticket_id)

        # Apply patches to worktree
        await milestone("apply_patches", "running")
        if not patches:
            raise RuntimeError(
                "No code file blocks found in agent output. "
                "Expected ### `path/to/file` blocks with code fences."
            )
        written = apply_patches(wt_path, patches)
        await milestone("apply_patches", "done", f"{len(written)} file(s)")
        await milestone("implement", "done")

        # Commit, push, and open PR
        await milestone("commit_push", "running")
        branch, pr_url = publish_ticket_changes(
            repo_path=primary_repo,
            worktree_path=wt_path,
            ticket_key=ticket.get("key") or ticket_id,
            title=ticket.get("title") or "Jira ticket fix",
            body=full_output[:12000],
            jira_url=ticket.get("jira_url") or "",
        )
        db.update_ticket(ticket_id, pr_url=pr_url, status="done")
        await milestone("commit_push", "done", branch)
        await milestone("create_pr", "done", pr_url)
        await emit("pr_created", AGENT, pr_url, ticket_id)

        await emit("agent_done", AGENT, f"Finished {ticket.get('key', ticket_id)}", ticket_id)
        await emit("ticket_done", AGENT, f"PR opened: {pr_url}", ticket_id)

    except Exception as e:
        err = str(e)
        existing = db.get_ticket(ticket_id) or {}
        preserved = (existing.get("output") or "").strip()
        output = preserved if preserved else err
        if preserved and preserved != err:
            output = preserved + f"\n\n---\n\n**Error:** {err}"
        db.update_ticket(ticket_id, status="error", output=output)
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
    if not repo_path:
        await send(json.dumps({"type": "error", "agent": "system", "data": "repo_context_path is required"}))
        return

    # Pick best coding model for Jira work
    if project["provider"] == "ollama":
        model = (
            config.SENIOR_DEV_MODEL
            or config.AGENT_MODELS.get("senior_dev")
            or pick_best_installed(ollama_list_models())
            or config.OLLAMA_MODEL
        )
        config.AGENT_MODELS["senior_dev"] = model
        db.update_project(project_id, model=model)

    db.update_project(project_id, status="running")

    sem = asyncio.Semaphore(config.JIRA_MAX_PARALLEL)

    async def run_one(ticket_row):
        async with sem:
            try:
                await run_ticket(project, ticket_row, send)
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
