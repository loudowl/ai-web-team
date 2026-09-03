"""SQLite persistence layer for projects, agent runs, and artifacts."""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

import config


def _conn():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    c = sqlite3.connect(config.DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            brief       TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'pending',
            provider    TEXT NOT NULL DEFAULT 'openai',
            model       TEXT,
            github_url  TEXT,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agent_runs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  TEXT NOT NULL,
            agent       TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'pending',
            output      TEXT,
            started_at  TEXT,
            finished_at TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS artifacts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  TEXT NOT NULL,
            agent       TEXT NOT NULL,
            filename    TEXT NOT NULL,
            content     TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS tickets (
            id                  TEXT PRIMARY KEY,
            project_id          TEXT NOT NULL,
            ticket_key          TEXT,
            title               TEXT NOT NULL,
            description         TEXT,
            jira_url            TEXT,
            acceptance_criteria TEXT,
            status              TEXT NOT NULL DEFAULT 'pending',
            worktree_path       TEXT,
            output              TEXT,
            tasks_json          TEXT,
            created_at          TEXT NOT NULL,
            updated_at          TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );
        """)
        _migrate(c)


def _migrate(c):
    """Add columns/tables for older DBs."""
    cols = {row[1] for row in c.execute("PRAGMA table_info(projects)").fetchall()}
    if "mode" not in cols:
        c.execute("ALTER TABLE projects ADD COLUMN mode TEXT NOT NULL DEFAULT 'greenfield'")
    if "repo_context_path" not in cols:
        c.execute("ALTER TABLE projects ADD COLUMN repo_context_path TEXT")

    ticket_cols = {row[1] for row in c.execute("PRAGMA table_info(tickets)").fetchall()}
    if "pr_url" not in ticket_cols:
        c.execute("ALTER TABLE tickets ADD COLUMN pr_url TEXT")
    if "board_lane" not in ticket_cols:
        c.execute("ALTER TABLE tickets ADD COLUMN board_lane TEXT NOT NULL DEFAULT 'todo'")
    if "workflow" not in ticket_cols:
        c.execute("ALTER TABLE tickets ADD COLUMN workflow TEXT")
    if "archived_at" not in ticket_cols:
        c.execute("ALTER TABLE tickets ADD COLUMN archived_at TEXT")
    if "fix_version" not in ticket_cols:
        c.execute("ALTER TABLE tickets ADD COLUMN fix_version TEXT")
    if "collab_branch" not in ticket_cols:
        c.execute("ALTER TABLE tickets ADD COLUMN collab_branch TEXT")


# ── Projects ──────────────────────────────────────────────────────────────────

def create_project(
    project_id: str,
    name: str,
    brief: str,
    provider: str,
    model: str,
    mode: str = "greenfield",
    repo_context_path: str = None,
) -> Dict:
    now = datetime.utcnow().isoformat()
    with _conn() as c:
        c.execute(
            """INSERT INTO projects
               (id, name, brief, status, provider, model, mode, repo_context_path, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (project_id, name, brief, "pending", provider, model, mode, repo_context_path, now, now),
        )
    return get_project(project_id)


def get_project(project_id: str) -> Optional[Dict]:
    with _conn() as c:
        row = c.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    return dict(row) if row else None


def list_projects(limit: int = 20) -> List[Dict]:
    with _conn() as c:
        rows = c.execute(
            """
            SELECT p.*,
                   (SELECT COUNT(*) FROM tickets t
                    WHERE t.project_id = p.id AND t.archived_at IS NULL) AS ticket_count,
                   (SELECT COUNT(*) FROM tickets t
                    WHERE t.project_id = p.id AND t.archived_at IS NULL
                      AND COALESCE(t.board_lane, 'todo') = 'in_progress') AS in_progress_count
            FROM projects p
            ORDER BY p.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def update_project(project_id: str, **kwargs):
    kwargs["updated_at"] = datetime.utcnow().isoformat()
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [project_id]
    with _conn() as c:
        c.execute(f"UPDATE projects SET {sets} WHERE id=?", vals)


def delete_project(project_id: str) -> bool:
    with _conn() as c:
        row = c.execute("SELECT id FROM projects WHERE id=?", (project_id,)).fetchone()
        if not row:
            return False
        c.execute("DELETE FROM tickets WHERE project_id=?", (project_id,))
        c.execute("DELETE FROM agent_runs WHERE project_id=?", (project_id,))
        c.execute("DELETE FROM artifacts WHERE project_id=?", (project_id,))
        c.execute("DELETE FROM projects WHERE id=?", (project_id,))
    return True


# ── Agent runs ────────────────────────────────────────────────────────────────

def upsert_agent_run(project_id: str, agent: str, status: str, output: str = None):
    now = datetime.utcnow().isoformat()
    with _conn() as c:
        existing = c.execute(
            "SELECT id FROM agent_runs WHERE project_id=? AND agent=?",
            (project_id, agent)
        ).fetchone()
        if existing:
            if output is not None:
                c.execute(
                    "UPDATE agent_runs SET status=?, output=?, finished_at=? WHERE project_id=? AND agent=?",
                    (status, output, now, project_id, agent)
                )
            else:
                c.execute(
                    "UPDATE agent_runs SET status=?, started_at=? WHERE project_id=? AND agent=?",
                    (status, now, project_id, agent)
                )
        else:
            c.execute(
                "INSERT INTO agent_runs (project_id, agent, status, started_at) VALUES (?,?,?,?)",
                (project_id, agent, status, now)
            )


def get_agent_runs(project_id: str) -> List[Dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM agent_runs WHERE project_id=? ORDER BY id",
            (project_id,)
        ).fetchall()
    return [dict(r) for r in rows]


# ── Artifacts ─────────────────────────────────────────────────────────────────

def save_artifact(project_id: str, agent: str, filename: str, content: str):
    now = datetime.utcnow().isoformat()
    with _conn() as c:
        c.execute(
            "INSERT INTO artifacts (project_id, agent, filename, content, created_at) VALUES (?,?,?,?,?)",
            (project_id, agent, filename, content, now)
        )


def get_artifacts(project_id: str) -> List[Dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM artifacts WHERE project_id=? ORDER BY id",
            (project_id,)
        ).fetchall()
    return [dict(r) for r in rows]


# ── Tickets (Jira mode) ───────────────────────────────────────────────────────

def create_ticket(
    ticket_id: str,
    project_id: str,
    title: str,
    description: str = "",
    ticket_key: str = None,
    jira_url: str = None,
    acceptance_criteria: str = "",
    tasks_json: str = None,
    board_lane: str = "todo",
    fix_version: str = None,
) -> Dict:
    now = datetime.utcnow().isoformat()
    with _conn() as c:
        c.execute(
            """INSERT INTO tickets
               (id, project_id, ticket_key, title, description, jira_url,
                acceptance_criteria, status, tasks_json, board_lane, fix_version, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                ticket_id, project_id, ticket_key, title, description, jira_url,
                acceptance_criteria, "pending", tasks_json, board_lane, fix_version, now, now,
            ),
        )
    return get_ticket(ticket_id)


def get_ticket(ticket_id: str) -> Optional[Dict]:
    with _conn() as c:
        row = c.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
    return dict(row) if row else None


def list_tickets(project_id: str, include_archived: bool = False) -> List[Dict]:
    with _conn() as c:
        if include_archived:
            rows = c.execute(
                "SELECT * FROM tickets WHERE project_id=? ORDER BY created_at",
                (project_id,),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM tickets WHERE project_id=? AND archived_at IS NULL ORDER BY created_at",
                (project_id,),
            ).fetchall()
    return [dict(r) for r in rows]


def list_all_board_tickets(limit: int = 500) -> List[Dict]:
    """All non-archived Jira tickets across projects for the global board."""
    with _conn() as c:
        rows = c.execute(
            """
            SELECT t.*,
                   p.name AS project_name,
                   p.provider AS project_provider,
                   p.model AS project_model,
                   p.repo_context_path AS project_repo_context_path,
                   p.status AS project_status
            FROM tickets t
            INNER JOIN projects p ON p.id = t.project_id
            WHERE p.mode = 'jira' AND t.archived_at IS NULL
            ORDER BY t.created_at ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_latest_jira_project() -> Optional[Dict]:
    projects = list_projects(limit=50)
    for project in projects:
        if project.get("mode") == "jira":
            return project
    return None


def list_archived_tickets(project_id: str = None, limit: int = 100) -> List[Dict]:
    with _conn() as c:
        if project_id:
            rows = c.execute(
                """SELECT * FROM tickets WHERE project_id=? AND archived_at IS NOT NULL
                   ORDER BY archived_at DESC LIMIT ?""",
                (project_id, limit),
            ).fetchall()
        else:
            rows = c.execute(
                """SELECT * FROM tickets WHERE archived_at IS NOT NULL
                   ORDER BY archived_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]


def update_ticket(ticket_id: str, **kwargs):
    kwargs["updated_at"] = datetime.utcnow().isoformat()
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [ticket_id]
    with _conn() as c:
        c.execute(f"UPDATE tickets SET {sets} WHERE id=?", vals)
