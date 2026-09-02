"""WebSocket endpoint — streams agent pipeline events to the mobile app."""

import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import database as db
from agents.runner import run_pipeline
from agents.jira_runner import run_jira_pipeline

router = APIRouter()

# Active connections: project_id → list of WebSockets
_connections: dict[str, list[WebSocket]] = {}


@router.websocket("/ws/{project_id}")
async def ws_pipeline(websocket: WebSocket, project_id: str):
    await websocket.accept()

    project = db.get_project(project_id)
    if not project:
        await websocket.send_text(json.dumps({"type": "error", "agent": "system", "data": "Project not found"}))
        await websocket.close()
        return

    # Register connection
    _connections.setdefault(project_id, []).append(websocket)

    async def send(msg: str):
        """Broadcast to all connected sockets for this project."""
        for ws in list(_connections.get(project_id, [])):
            try:
                await ws.send_text(msg)
            except Exception:
                pass

    try:
        mode = project.get("mode") or "greenfield"

        # If pipeline already ran, replay artifacts and close
        if project["status"] == "done":
            if mode == "jira":
                tickets = db.list_tickets(project_id)
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
                    if t.get("tasks_json"):
                        await send(json.dumps({
                            "type": "tasks",
                            "agent": "senior_dev",
                            "ticket_id": t["id"],
                            "data": t["tasks_json"],
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

        if mode == "jira":
            await run_jira_pipeline(project_id=project_id, send=send)
        else:
            await run_pipeline(
                project_id=project_id,
                brief=project["brief"],
                provider=project["provider"],
                send=send,
            )

    except WebSocketDisconnect:
        pass
    finally:
        conns = _connections.get(project_id, [])
        if websocket in conns:
            conns.remove(websocket)
