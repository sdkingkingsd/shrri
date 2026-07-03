"""
Workflow Recorder — SHRRI Phase 11
Records successful workflows so they can be replayed later.
"""
import sqlite3, os, json
from datetime import datetime

DB_PATH = os.path.expanduser("~/.shrri/workflows.db")


class WorkflowRecorder:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._init_tables()
        self._initialized = True

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS workflows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                trigger TEXT,
                steps TEXT,
                success_count INTEGER DEFAULT 1,
                last_used TEXT,
                created_at TEXT
            );
        """)
        self.conn.commit()

    def record(self, name: str, trigger: str, steps: list) -> int:
        existing = self.conn.execute(
            "SELECT id, success_count FROM workflows WHERE name=?", (name,)
        ).fetchone()
        now = datetime.now().isoformat()
        if existing:
            self.conn.execute(
                "UPDATE workflows SET success_count=success_count+1, last_used=?, steps=? WHERE id=?",
                (now, json.dumps(steps), existing[0])
            )
            self.conn.commit()
            return existing[0]
        cur = self.conn.execute(
            "INSERT INTO workflows (name, trigger, steps, last_used, created_at) VALUES (?,?,?,?,?)",
            (name, trigger, json.dumps(steps), now, now)
        )
        self.conn.commit()
        return cur.lastrowid

    def get(self, name: str) -> dict:
        row = self.conn.execute(
            "SELECT name, trigger, steps, success_count FROM workflows WHERE name=?", (name,)
        ).fetchone()
        if not row:
            return {}
        return {"name": row[0], "trigger": row[1],
                "steps": json.loads(row[2]), "success_count": row[3]}

    def find_by_trigger(self, trigger: str) -> list:
        rows = self.conn.execute(
            "SELECT name, trigger, steps, success_count FROM workflows ORDER BY success_count DESC"
        ).fetchall()
        trigger_words = set(trigger.lower().split())
        matches = []
        for r in rows:
            wf_words = set(r[1].lower().split())
            if len(trigger_words & wf_words) >= 2:
                matches.append({"name": r[0], "trigger": r[1],
                                 "steps": json.loads(r[2]), "success_count": r[3]})
        return matches

    def list_all(self) -> list:
        rows = self.conn.execute(
            "SELECT name, trigger, success_count, last_used FROM workflows ORDER BY success_count DESC"
        ).fetchall()
        return [{"name": r[0], "trigger": r[1],
                 "count": r[2], "last_used": r[3][:10]} for r in rows]
