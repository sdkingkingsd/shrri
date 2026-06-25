import sqlite3
import os
from datetime import datetime

class GapLogger:
    def __init__(self, conn):
        self.conn = conn
        self._init_table()

    def _init_table(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS gaps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                message TEXT,
                error TEXT,
                resolved INTEGER DEFAULT 0,
                timestamp TEXT
            );
        """)
        self.conn.commit()

    def log_gap(self, category: str, message: str, error: str = ""):
        """Record a failure or unmet need."""
        self.conn.execute("""
            INSERT INTO gaps (category, message, error, timestamp)
            VALUES (?, ?, ?, ?)
        """, (category, message[:300], error[:500], datetime.now().isoformat()))
        self.conn.commit()

    def get_unresolved(self, limit=10):
        rows = self.conn.execute("""
            SELECT id, category, message, error, timestamp
            FROM gaps WHERE resolved=0
            ORDER BY id DESC LIMIT ?
        """, (limit,)).fetchall()
        return [
            {"id": r[0], "category": r[1], "message": r[2], "error": r[3], "timestamp": r[4]}
            for r in rows
        ]

    def mark_resolved(self, gap_id: int):
        self.conn.execute("UPDATE gaps SET resolved=1 WHERE id=?", (gap_id,))
        self.conn.commit()
