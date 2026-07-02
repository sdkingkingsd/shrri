"""
Checkpoint Manager — SHRRI AI OS v2 (Phase 4)

Persists workflow/task-queue state to disk so a crash or restart
doesn't lose progress on a multi-step goal. Follows the same
SQLite-under-~/.shrri convention as runner/persistence.py, kept in
its own table/file so workflow checkpoints are independent of
conversation session storage.

A "checkpoint" here is: given a workflow_id, save/load the full
serialized state of its TaskQueue (all tasks + statuses) as JSON.
"""

import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path.home() / ".shrri" / "checkpoints.db"


class CheckpointManager:
    def __init__(self, db_path: Path = DB_PATH):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                workflow_id TEXT PRIMARY KEY,
                state_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        self.conn.commit()

    def save(self, workflow_id: str, state: dict) -> None:
        """Save (or overwrite) the checkpoint for a workflow_id."""
        now = time.time()
        state_json = json.dumps(state)
        self.conn.execute("""
            INSERT INTO checkpoints (workflow_id, state_json, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(workflow_id) DO UPDATE SET
                state_json=excluded.state_json,
                updated_at=excluded.updated_at
        """, (workflow_id, state_json, now, now))
        self.conn.commit()

    def load(self, workflow_id: str) -> dict | None:
        """Load the checkpoint for a workflow_id, or None if none exists."""
        row = self.conn.execute(
            "SELECT state_json FROM checkpoints WHERE workflow_id = ?",
            (workflow_id,)
        ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def delete(self, workflow_id: str) -> None:
        """Remove a checkpoint — call this once a workflow completes
        successfully, so completed workflows don't accumulate forever."""
        self.conn.execute("DELETE FROM checkpoints WHERE workflow_id = ?", (workflow_id,))
        self.conn.commit()

    def list_workflow_ids(self) -> list[str]:
        rows = self.conn.execute("SELECT workflow_id FROM checkpoints").fetchall()
        return [r[0] for r in rows]
