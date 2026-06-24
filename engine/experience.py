import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.expanduser("~/.shrri/memory.db")

class Experience:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self._init_table()

    def _init_table(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS experiences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT,
                outcome TEXT,
                detail TEXT,
                timestamp TEXT
            );
        """)
        self.conn.commit()

    def log(self, task, outcome, detail=""):
        self.conn.execute(
            "INSERT INTO experiences (task, outcome, detail, timestamp) VALUES (?, ?, ?, ?)",
            (task, outcome, detail, datetime.now().isoformat())
        )
        self.conn.commit()

    def recall(self, task_keyword, limit=5):
        rows = self.conn.execute(
            "SELECT task, outcome, detail, timestamp FROM experiences WHERE task LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{task_keyword}%", limit)
        ).fetchall()
        return [{"task": r[0], "outcome": r[1], "detail": r[2], "timestamp": r[3]} for r in rows]

    def all(self, limit=20):
        rows = self.conn.execute(
            "SELECT task, outcome, detail, timestamp FROM experiences ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [{"task": r[0], "outcome": r[1], "detail": r[2], "timestamp": r[3]} for r in rows]
