import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from .config import settings


def now() -> str:
    return datetime.now(UTC).isoformat()


def uid() -> str:
    return uuid4().hex


def encode(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True, ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(encode(value).encode()).hexdigest()


@contextmanager
def connect():
    settings().data_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings().data_dir / "marginguard.sqlite3", timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=15000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize():
    with connect() as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.executescript("""
        CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY);
        INSERT OR IGNORE INTO schema_version VALUES(1);
        CREATE TABLE IF NOT EXISTS users(
            id TEXT PRIMARY KEY, email TEXT UNIQUE, name TEXT NOT NULL,
            password_hash TEXT, is_demo INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS workspaces(
            id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL, active_dataset_id TEXT,
            scenario_json TEXT NOT NULL DEFAULT '{}', scenario_hash TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS workspace_owner ON workspaces(owner_id);
        CREATE TABLE IF NOT EXISTS sessions(
            token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            csrf TEXT NOT NULL, expires_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS datasets(
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            version INTEGER NOT NULL, name TEXT NOT NULL, content_hash TEXT NOT NULL,
            snapshot TEXT NOT NULL, summary TEXT NOT NULL, issues TEXT NOT NULL,
            status TEXT NOT NULL, synthetic INTEGER NOT NULL, created_at TEXT NOT NULL,
            UNIQUE(workspace_id,version)
        );
        CREATE TABLE IF NOT EXISTS runs(
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            dataset_id TEXT NOT NULL REFERENCES datasets(id), question TEXT NOT NULL,
            status TEXT NOT NULL, mode TEXT NOT NULL, stage TEXT NOT NULL,
            events TEXT NOT NULL DEFAULT '[]', result TEXT, state TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL, finished_at TEXT
        );
        CREATE INDEX IF NOT EXISTS runs_workspace ON runs(workspace_id,created_at);
        CREATE TABLE IF NOT EXISTS memos(
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            dataset_id TEXT NOT NULL REFERENCES datasets(id), scenario_hash TEXT NOT NULL,
            content TEXT NOT NULL, status TEXT NOT NULL, approved_by TEXT,
            created_at TEXT NOT NULL, approved_at TEXT
        );
        CREATE TABLE IF NOT EXISTS audit(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            action TEXT NOT NULL, details TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS rate_limits(
            bucket TEXT PRIMARY KEY, count INTEGER NOT NULL, reset_at REAL NOT NULL
        );
        """)
        # In-flight jobs are recoverable instead of being silently abandoned on a restart.
        c.execute(
            "UPDATE runs SET status='interrupted',stage='Resume available' WHERE status IN ('running','queued')"
        )


def audit(c, workspace: str, action: str, details: dict):
    c.execute(
        "INSERT INTO audit(workspace_id,action,details,created_at) VALUES(?,?,?,?)",
        (workspace, action, encode(details), now()),
    )


def stale_memos(c, workspace: str):
    c.execute("UPDATE memos SET status='stale' WHERE workspace_id=? AND status!='stale'", (workspace,))
