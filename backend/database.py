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
        """)


# ── Projects ──────────────────────────────────────────────────────────────────

def create_project(project_id: str, name: str, brief: str, provider: str, model: str) -> Dict:
    now = datetime.utcnow().isoformat()
    with _conn() as c:
        c.execute(
            "INSERT INTO projects (id, name, brief, status, provider, model, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (project_id, name, brief, "pending", provider, model, now, now)
        )
    return get_project(project_id)


def get_project(project_id: str) -> Optional[Dict]:
    with _conn() as c:
        row = c.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    return dict(row) if row else None


def list_projects(limit: int = 20) -> List[Dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM projects ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def update_project(project_id: str, **kwargs):
    kwargs["updated_at"] = datetime.utcnow().isoformat()
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [project_id]
    with _conn() as c:
        c.execute(f"UPDATE projects SET {sets} WHERE id=?", vals)


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
