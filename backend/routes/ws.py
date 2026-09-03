"""WebSocket endpoint — streams agent pipeline events to the web app."""

import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import database as db
from agents.runner import run_pipeline
from agents.jira_runner import run_jira_pipeline, replay_board_state
from routes.ws_hub import register, unregister, broadcast

router = APIRouter()


@router.websocket("/ws/{project_id}")
async def ws_pipeline(websocket: WebSocket, project_id: str):
    await websocket.accept()

    project = db.get_project(project_id)
    if not project:
        await websocket.send_text(json.dumps({"type": "error", "agent": "system", "data": "Project not found"}))
        await websocket.close()
        return

    register(project_id, websocket)

    async def send(msg: str):
        await broadcast(project_id, msg)

    try:
        mode = project.get("mode") or "greenfield"

        if project["status"] == "done":
            if mode == "jira":
                tickets = db.list_tickets(project_id, include_archived=False)
                for t in tickets:
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
                    if t.get("board_lane"):
                        await send(json.dumps({
                            "type": "board_lane",
                            "agent": "system",
                            "ticket_id": t["id"],
                            "data": t["board_lane"],
                        }))
            else:
                agents = db.get_agent_runs(project_id)
                for run in agents:
                    if run.get("output"):
                        await send(json.dumps({
                            "type":  "replay",
                            "agent": run["agent"],
                            "data":  run["output"],
                        }))
            await send(json.dumps({"type": "pipeline_done", "agent": "system", "data": "Pipeline already complete."}))
            return

        if mode == "jira" and project["status"] in ("pending", "ready", "running"):
            if project["status"] == "pending":
                db.update_project(project_id, status="ready")
            await replay_board_state(project_id, send)
            while True:
                await websocket.receive_text()
            return

        if mode == "jira":
            # Legacy: auto-run all tickets (avoid for board batches — use per-ticket launch)
            await run_jira_pipeline(project_id=project_id, send=send)
        else:
            await run_pipeline(
                project_id=project_id,
                brief=project["brief"],
                provider=project["provider"],
                send=send,
                model=project.get("model"),
            )

    except WebSocketDisconnect:
        pass
    finally:
        unregister(project_id, websocket)
