"""
Agent runner — orchestrates the 4-agent pipeline and streams events
back to connected WebSocket clients.

Event envelope (JSON):
  { "type": "agent_start"|"token"|"agent_done"|"error"|"pipeline_done",
    "agent": "pm"|"designer"|"architect"|"developer",
    "data":  string }
"""

import asyncio
import json
from typing import Callable, Awaitable

import database as db
from models.providers import stream_response
from agents.prompts import (
    PM_SYSTEM, DESIGNER_SYSTEM, ARCHITECT_SYSTEM, DEVELOPER_SYSTEM,
    pm_prompt, designer_prompt, architect_prompt, developer_prompt,
)

AGENTS = ["pm", "designer", "architect", "developer"]

AGENT_LABELS = {
    "pm":        "Project Manager",
    "designer":  "Designer",
    "architect": "Architect",
    "developer": "Developer",
}

AGENT_SYSTEMS = {
    "pm":        PM_SYSTEM,
    "designer":  DESIGNER_SYSTEM,
    "architect": ARCHITECT_SYSTEM,
    "developer": DEVELOPER_SYSTEM,
}


async def run_pipeline(
    project_id: str,
    brief: str,
    provider: str,
    send: Callable[[str], Awaitable[None]],
):
    """
    Run all 4 agents sequentially, streaming tokens via `send(json_str)`.
    Each agent's output is persisted and passed to the next.
    """
    outputs = {}

    async def emit(type_: str, agent: str, data: str):
        await send(json.dumps({"type": type_, "agent": agent, "data": data}))

    db.update_project(project_id, status="running")

    for agent in AGENTS:
        label = AGENT_LABELS[agent]
        await emit("agent_start", agent, f"Starting {label}...")
        db.upsert_agent_run(project_id, agent, "running")

        # Build the prompt for this agent
        if agent == "pm":
            prompt = pm_prompt(brief)
        elif agent == "designer":
            prompt = designer_prompt(brief, outputs.get("pm", ""))
        elif agent == "architect":
            prompt = architect_prompt(brief, outputs.get("pm", ""), outputs.get("designer", ""))
        else:  # developer
            prompt = developer_prompt(
                brief,
                outputs.get("pm", ""),
                outputs.get("designer", ""),
                outputs.get("architect", ""),
            )

        full_output = []
        try:
            # Run sync generator in a thread pool so we don't block the event loop
            loop = asyncio.get_event_loop()
            gen = stream_response(
                prompt=prompt,
                provider=provider,
                agent=agent,
                system=AGENT_SYSTEMS[agent],
            )

            def _next_chunk():
                try:
                    return next(gen)
                except StopIteration:
                    return None

            while True:
                chunk = await loop.run_in_executor(None, _next_chunk)
                if chunk is None:
                    break
                full_output.append(chunk)
                await emit("token", agent, chunk)

            output_text = "".join(full_output)
            outputs[agent] = output_text

            db.upsert_agent_run(project_id, agent, "done", output_text)
            db.save_artifact(project_id, agent, f"{agent}_output.md", output_text)
            await emit("agent_done", agent, f"{label} finished.")

        except Exception as e:
            err = f"❌ {label} failed: {e}"
            db.upsert_agent_run(project_id, agent, "error", str(e))
            await emit("error", agent, err)
            db.update_project(project_id, status="error")
            return

    db.update_project(project_id, status="done")
    await emit("pipeline_done", "system", "All agents finished. Ready to push to GitHub.")
