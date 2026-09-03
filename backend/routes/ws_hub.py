"""WebSocket connection registry and broadcast helpers."""

import asyncio
from typing import Awaitable, Callable, Dict, Set

from fastapi import WebSocket

_connections: Dict[str, list] = {}
_running_tickets: Set[str] = set()


def register(project_id: str, websocket: WebSocket):
    _connections.setdefault(project_id, []).append(websocket)


def unregister(project_id: str, websocket: WebSocket):
    conns = _connections.get(project_id, [])
    if websocket in conns:
        conns.remove(websocket)


async def broadcast(project_id: str, message: str):
    for ws in list(_connections.get(project_id, [])):
        try:
            await ws.send_text(message)
        except Exception:
            pass


def ticket_run_key(project_id: str, ticket_id: str) -> str:
    return f"{project_id}:{ticket_id}"


def is_ticket_running(project_id: str, ticket_id: str) -> bool:
    return ticket_run_key(project_id, ticket_id) in _running_tickets


def mark_ticket_running(project_id: str, ticket_id: str) -> bool:
    key = ticket_run_key(project_id, ticket_id)
    if key in _running_tickets:
        return False
    _running_tickets.add(key)
    return True


def mark_ticket_done(project_id: str, ticket_id: str):
    _running_tickets.discard(ticket_run_key(project_id, ticket_id))


def schedule_ticket_run(
    project_id: str,
    ticket_id: str,
    workflow: str,
    runner: Callable[[str, str, str, Callable[[str], Awaitable[None]]], Awaitable[None]],
):
    """Fire-and-forget single ticket run; broadcasts via WS."""

    async def _job():
        if not mark_ticket_running(project_id, ticket_id):
            return

        async def send(msg: str):
            await broadcast(project_id, msg)

        try:
            await runner(project_id, ticket_id, workflow, send)
        finally:
            mark_ticket_done(project_id, ticket_id)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError as exc:
        raise RuntimeError(
            "schedule_ticket_run must be called from an async request handler"
        ) from exc
    loop.create_task(_job())
