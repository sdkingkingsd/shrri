"""
Session Persistence — SHRRI AI OS v2

Simple SQLite-backed persistence for SessionManager. Dumps/loads full
session state so a bot restart doesn't lose active conversations.

Kept separate from session_manager.py so the in-memory manager stays
swappable/testable without a DB dependency.
"""

import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path.home() / ".shrri" / "sessions.db"


class SessionStore:
    def __init__(self, db_path: Path = DB_PATH):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                channel TEXT NOT NULL,
                peer_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                permission_tier TEXT NOT NULL,
                history_json TEXT NOT NULL,
                workflow_state_json TEXT,
                created_at REAL NOT NULL,
                last_active REAL NOT NULL,
                PRIMARY KEY (channel, peer_id)
            )
        """)
        self.conn.commit()

    def save(self, session) -> None:
        self.conn.execute("""
            INSERT INTO sessions
                (channel, peer_id, session_id, permission_tier, history_json,
                 workflow_state_json, created_at, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(channel, peer_id) DO UPDATE SET
                session_id=excluded.session_id,
                permission_tier=excluded.permission_tier,
                history_json=excluded.history_json,
                workflow_state_json=excluded.workflow_state_json,
                last_active=excluded.last_active
        """, (
            session.channel, session.peer_id, session.session_id,
            session.permission_tier, json.dumps(session.history),
            json.dumps(session.workflow_state) if session.workflow_state else None,
            session.created_at, session.last_active,
        ))
        self.conn.commit()

    def load_all(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM sessions").fetchall()
        cols = [d[0] for d in self.conn.execute("SELECT * FROM sessions").description]
        results = []
        for row in rows:
            d = dict(zip(cols, row))
            d["history"] = json.loads(d.pop("history_json"))
            wf = d.pop("workflow_state_json")
            d["workflow_state"] = json.loads(wf) if wf else None
            results.append(d)
        return results

    def delete(self, channel: str, peer_id: str) -> None:
        self.conn.execute(
            "DELETE FROM sessions WHERE channel=? AND peer_id=?", (channel, peer_id)
        )
        self.conn.commit()
