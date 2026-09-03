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
from models.providers import resolve_ollama_model
from agents.prompts import (
    SENIOR_DEV_SYSTEM,
    CODE_REVIEW_SYSTEM,
    JIRA_MILESTONES,
    jira_analyze_prompt,
    jira_implement_prompt,
    jira_implement_retry_prompt,
    jira_lint_fix_prompt,
    jira_copilot_review_prompt,
)
from utils.repo_context import build_repo_context, list_repos
from utils.git_worktree import ensure_worktree
from utils.jira_client import fetch_ticket
from utils.collab_branch import resolve_collab_base_branch
from utils.patch_apply import apply_patches, parse_code_blocks
from utils.lint_runner import run_lint, run_lint_fix
from utils.github_pr import (
    branch_name,
    commit_and_push_ticket,
    open_ticket_pull_request,
    parse_github_remote,
    parse_pr_number,
    wait_for_copilot_feedback,
    is_bot_reviewer,
    push_followup_commit,
)

AGENT = "senior_dev"
REVIEWER = "code_reviewer"

WORKFLOW_PRESETS = {
    "simple": {"lint": True, "copilot": True, "copilot_wait": None},
    "fix": {"lint": True, "copilot": False, "copilot_wait": None},
    "full_cycle": {"lint": True, "copilot": True, "copilot_wait": 120},
}


def _configure_jira_models(project: dict) -> str:
    """Resolve senior_dev model for a Jira project; returns the Ollama tag in use."""
    if project.get("provider") != "ollama":
        if project.get("model"):
            config.AGENT_MODELS["senior_dev"] = project["model"]
        return project.get("model") or ""

    requested = project.get("model") or config.SENIOR_DEV_MODEL or config.OLLAMA_MODEL
    model = resolve_ollama_model(requested, allow_fallback=not bool(project.get("model")))
    config.AGENT_MODELS["senior_dev"] = model
    review_model = config.AGENT_MODELS.get("code_reviewer") or model
    config.AGENT_MODELS["code_reviewer"] = review_model
    return model


async def replay_board_state(project_id: str, send: Callable[[str], Awaitable[None]]):
    """Send current ticket board state to a newly connected client."""
    for t in db.list_tickets(project_id):
        if t.get("archived_at"):
            continue
        lane = t.get("board_lane") or "todo"
        if t.get("status") == "running":
            lane = "in_progress"
        await send(json.dumps({
            "type": "board_lane",
            "agent": "system",
            "ticket_id": t["id"],
            "data": lane,
        }))
        if t.get("output"):
            await send(json.dumps({
                "type": "replay",
                "agent": "senior_dev",
                "ticket_id": t["id"],
                "data": t["output"],
            }))
        if t.get("pr_url"):
            await send(json.dumps({
                "type": "pr_created",
                "agent": "senior_dev",
                "ticket_id": t["id"],
                "data": t["pr_url"],
            }))


async def run_single_ticket(
    project_id: str,
    ticket_id: str,
    workflow: str,
    send: Callable[[str], Awaitable[None]],
):
    project = db.get_project(project_id)
    if not project:
        raise ValueError("Project not found")
    ticket_row = db.get_ticket(ticket_id)
    if not ticket_row or ticket_row["project_id"] != project_id:
        raise ValueError("Ticket not found")

    if project.get("provider") == "ollama":
        _configure_jira_models(project)

    if project["status"] == "pending":
        db.update_project(project_id, status="ready")

    preset = WORKFLOW_PRESETS.get(workflow, WORKFLOW_PRESETS["simple"])
    try:
        await run_ticket(project, ticket_row, send, workflow=preset)
    except Exception:
        raise
    finally:
        tickets = db.list_tickets(project_id, include_archived=False)
        open_tickets = [t for t in tickets if t["status"] in ("pending", "running", "error")]
        if open_tickets:
            db.update_project(project_id, status="ready")
        elif any(t["status"] == "error" for t in tickets):
            db.update_project(project_id, status="error")
        else:
            db.update_project(project_id, status="ready")


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
    agent_role: str = AGENT,
    system: str = None,
    model: str = None,
) -> str:
    loop = asyncio.get_event_loop()
    system = system or (CODE_REVIEW_SYSTEM if agent_role == REVIEWER else SENIOR_DEV_SYSTEM)
    gen = stream_response(
        prompt=prompt,
        provider=provider,
        agent=agent_role,
        system=system,
        model=model,
    )

    def _next_chunk():
        try:
            return next(gen)
        except StopIteration:
            return None

    await emit("thinking", agent_role, json.dumps({
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
                await emit("thinking", agent_role, json.dumps({
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
            await emit("token", agent_role, chunk, ticket_id)
    finally:
        pulsing = False
        heartbeat.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await heartbeat

    return "".join(full)


async def _run_lint_pipeline(
    wt_path: str,
    changed_files: List[str],
    ticket: dict,
    provider: str,
    ticket_id: str,
    emit,
    full_output: str,
    primary_repo: str = None,
    model: str = None,
) -> tuple[List[str], str]:
    """Auto-fix lint, then agent loop until clean or max rounds."""
    loop = asyncio.get_event_loop()
    files = list(changed_files)

    await emit("thinking", AGENT, json.dumps({
        "phase": "fix_lint",
        "message": "Running eslint --fix…",
    }), ticket_id)
    await loop.run_in_executor(
        None, lambda: run_lint_fix(wt_path, files, primary_repo),
    )

    output = full_output
    for round_num in range(config.JIRA_LINT_MAX_ROUNDS):
        lint = await loop.run_in_executor(
            None, lambda: run_lint(wt_path, files, primary_repo),
        )
        if lint.ok:
            return files, output

        await emit("thinking", AGENT, json.dumps({
            "phase": "fix_lint",
            "message": f"Lint failed (round {round_num + 1}) — asking agent to fix…",
        }), ticket_id)
        fix_prompt = jira_lint_fix_prompt(ticket, lint.output, files)
        fix_output = await _stream_agent(
            fix_prompt, provider, ticket_id, emit, phase="fix_lint",
            model=model,
        )
        output = output + f"\n\n---\n\n# Lint fix (round {round_num + 1})\n\n" + fix_output
        fix_patches = parse_code_blocks(fix_output)
        if not fix_patches:
            break
        written = apply_patches(wt_path, fix_patches)
        files = list(dict.fromkeys(files + written))

    final = await loop.run_in_executor(
        None, lambda: run_lint(wt_path, files, primary_repo),
    )
    if not final.ok:
        raise RuntimeError(
            "Lint still failing after fix attempts:\n"
            + (final.output[:4000] or "no lint output")
        )
    return files, output


async def run_ticket(
    project: dict,
    ticket_row: dict,
    send: Callable[[str], Awaitable[None]],
    workflow: dict = None,
):
    ticket_id = ticket_row["id"]
    provider = project["provider"]
    project_model = project.get("model")
    wf = workflow or WORKFLOW_PRESETS["simple"]
    lint_enabled = wf.get("lint", config.JIRA_LINT_ENABLED)
    copilot_enabled = wf.get("copilot", config.JIRA_COPILOT_REVIEW)
    copilot_wait = wf.get("copilot_wait") or config.JIRA_COPILOT_WAIT_SEC

    ticket = {
        "key": ticket_row.get("ticket_key"),
        "title": ticket_row.get("title"),
        "description": ticket_row.get("description"),
        "acceptance_criteria": ticket_row.get("acceptance_criteria"),
        "jira_url": ticket_row.get("jira_url"),
        "fix_version": ticket_row.get("fix_version") or "",
        "fix_versions": [ticket_row["fix_version"]] if ticket_row.get("fix_version") else [],
    }

    repo_path = project.get("repo_context_path") or config.REPO_CONTEXT_PATH

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

    async def set_board_lane(lane: str):
        db.update_ticket(ticket_id, board_lane=lane)
        await emit("board_lane", AGENT, lane, ticket_id)

    if ticket_row.get("jira_url") or ticket_row.get("ticket_key"):
        try:
            fresh = fetch_ticket(
                jira_url=ticket_row.get("jira_url"),
                ticket_key=ticket_row.get("ticket_key"),
            )
            ticket["title"] = fresh.get("title") or ticket["title"]
            ticket["description"] = fresh.get("description") or ticket["description"]
            ticket["acceptance_criteria"] = fresh.get("acceptance_criteria") or ticket["acceptance_criteria"]
            ticket["fix_versions"] = fresh.get("fix_versions") or []
            ticket["fix_version"] = fresh.get("fix_version") or ""
        except Exception as exc:
            await emit("thinking", AGENT, json.dumps({
                "phase": "fetch_ticket",
                "message": f"Could not refresh Jira ticket fields: {exc}",
            }), ticket_id)

    try:
        db.update_ticket(ticket_id, status="running", output="")
        await set_board_lane("in_progress")
        await emit("ticket_start", AGENT, f"Starting {ticket.get('key', ticket_id)}…", ticket_id)
        await emit("agent_start", AGENT, f"Senior Dev → {ticket.get('title', '')}", ticket_id)

        fetch_detail = ticket.get("fix_version") or "Ticket loaded"
        await milestone("fetch_ticket", "done", fetch_detail)
        await milestone("gather_context", "running", "Resolving collab branch…")

        repos = list_repos(__import__("pathlib").Path(repo_path).resolve())
        primary_repo = str(repos[0]) if repos else repo_path
        collab_branch, branch_reason = resolve_collab_base_branch(
            primary_repo,
            ticket.get("fix_versions") or [],
        )
        ticket["collab_branch"] = collab_branch
        db.update_ticket(
            ticket_id,
            fix_version=ticket.get("fix_version") or None,
            collab_branch=collab_branch,
        )
        ctx = build_repo_context(repo_path, ticket=ticket)
        analyze_repo_text = ctx["analyze_repo_text"]
        await milestone("gather_context", "done", f"{collab_branch} ({branch_reason})")

        # Worktree
        await milestone("create_worktree", "running", f"From {collab_branch}…")
        wt_path = ensure_worktree(
            primary_repo,
            project["id"],
            ticket_id,
            ticket_row.get("ticket_key"),
            base_branch=collab_branch,
        )
        db.update_ticket(ticket_id, worktree_path=wt_path)
        await milestone("create_worktree", "done", wt_path)

        # Plan
        await milestone("analyze_plan", "running")
        plan_prompt = jira_analyze_prompt(ticket, analyze_repo_text)
        plan_output = await _stream_agent(
            plan_prompt, provider, ticket_id, emit, phase="analyze_plan", model=project_model,
        )
        db.update_ticket(ticket_id, output=plan_output)
        _validate_plan(plan_output, ticket)
        tasks = _parse_task_list(plan_output)
        db.update_ticket(ticket_id, tasks_json=json.dumps(tasks))
        await emit("tasks", AGENT, json.dumps(tasks), ticket_id)
        await milestone("analyze_plan", "done")

        # Implement
        await milestone("implement", "running")
        impl_prompt = jira_implement_prompt(ticket, ctx["repo_text"], plan_output)
        impl_output = await _stream_agent(
            impl_prompt, provider, ticket_id, emit, phase="implement", model=project_model,
        )
        full_output = plan_output + "\n\n---\n\n# Implementation\n\n" + impl_output

        patches = parse_code_blocks(impl_output) or parse_code_blocks(full_output)
        if not patches:
            await emit("thinking", AGENT, json.dumps({
                "phase": "implement",
                "message": "No code blocks found — retrying with stricter format instructions…",
            }), ticket_id)
            retry_prompt = jira_implement_retry_prompt(ticket, plan_output)
            retry_output = await _stream_agent(
                retry_prompt, provider, ticket_id, emit, phase="implement", model=project_model,
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

        # Lint before PR
        await milestone("fix_lint", "running", "Checking lint…")
        if lint_enabled:
            written, full_output = await _run_lint_pipeline(
                wt_path, written, ticket, provider, ticket_id, emit, full_output,
                primary_repo=primary_repo, model=project_model,
            )
            db.update_ticket(ticket_id, output=full_output)
            await milestone("fix_lint", "done", "Lint passed")
        else:
            await milestone("fix_lint", "done", "Skipped")

        # Commit, push, and open PR
        await milestone("commit_push", "running")
        branch, _ = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: commit_and_push_ticket(
                wt_path,
                primary_repo,
                ticket.get("key") or ticket_id,
                ticket.get("title") or "Jira ticket fix",
            ),
        )
        await milestone("commit_push", "done", branch)

        await milestone("create_pr", "running")
        pr_url = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: open_ticket_pull_request(
                repo_path=primary_repo,
                branch=branch,
                ticket_key=ticket.get("key") or ticket_id,
                title=ticket.get("title") or "Jira ticket fix",
                body=full_output[:12000],
                jira_url=ticket.get("jira_url") or "",
                base_branch=collab_branch,
            ),
        )
        await milestone("create_pr", "done", pr_url)
        await emit("pr_created", AGENT, pr_url, ticket_id)
        await set_board_lane("in_review")

        # Address Copilot / bot review comments
        await milestone("address_review", "running", "Waiting for review…")
        review_detail = "Skipped"
        if copilot_enabled and config.GITHUB_TOKEN:
            owner, repo = parse_github_remote(primary_repo)
            pr_number = parse_pr_number(pr_url)
            if pr_number:
                loop = asyncio.get_event_loop()
                comments = await loop.run_in_executor(
                    None,
                    lambda: wait_for_copilot_feedback(
                        owner, repo, pr_number, copilot_wait,
                    ),
                )
                bot_comments = [c for c in comments if is_bot_reviewer(c.get("author"))]
                if bot_comments:
                    await emit("agent_start", REVIEWER, "Reviewing Copilot feedback…", ticket_id)
                    review_prompt = jira_copilot_review_prompt(ticket, bot_comments, written)
                    review_model = config.AGENT_MODELS.get("code_reviewer") or project_model
                    review_output = await _stream_agent(
                        review_prompt,
                        provider,
                        ticket_id,
                        emit,
                        phase="address_review",
                        agent_role=REVIEWER,
                        model=review_model,
                    )
                    if "NO_CRITICAL_FIXES" not in review_output.upper():
                        review_patches = parse_code_blocks(review_output)
                        if review_patches:
                            written = apply_patches(wt_path, review_patches)
                            if lint_enabled:
                                written, full_output = await _run_lint_pipeline(
                                    wt_path, written, ticket, provider, ticket_id, emit, full_output,
                                    primary_repo=primary_repo, model=project_model,
                                )
                            msg = f"{ticket.get('key') or ticket_id}: address Copilot review"
                            pushed = await loop.run_in_executor(
                                None,
                                lambda: push_followup_commit(wt_path, branch, msg[:500]),
                            )
                            review_detail = "Critical fixes pushed" if pushed else "No file changes"
                        else:
                            review_detail = "No patch output from reviewer"
                    else:
                        review_detail = "No critical fixes needed"
                    await emit("agent_done", REVIEWER, review_detail, ticket_id)
                else:
                    review_detail = "No Copilot comments yet"
        await milestone("address_review", "done", review_detail)

        db.update_ticket(ticket_id, pr_url=pr_url, status="done", output=full_output)

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

    # Resolve models for Jira work
    if project.get("provider") == "ollama":
        model = _configure_jira_models(project)
        if model and model != project.get("model"):
            db.update_project(project_id, model=model)
    elif project.get("model"):
        config.AGENT_MODELS["senior_dev"] = project["model"]

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
            fix_version=data.get("fix_version") or None,
        )
        created.append(row)
    return created
