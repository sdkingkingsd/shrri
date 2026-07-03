"""
Tracer — SHRRI Phase 12
Traces every LLM call: input, output, latency, provider, model.
"""
import sqlite3, os, time
from datetime import datetime

DB_PATH = os.path.expanduser("~/.shrri/traces.db")


class Tracer:
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
            CREATE TABLE IF NOT EXISTS traces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                provider TEXT,
                model TEXT,
                capability TEXT,
                prompt_tokens INTEGER,
                input TEXT,
                output TEXT,
                latency_ms REAL,
                success INTEGER,
                error TEXT,
                timestamp TEXT
            );
        """)
        self.conn.commit()

    def trace(self, session_id: str, provider: str, model: str,
              capability: str, input_text: str, output_text: str,
              latency_ms: float, success: bool, error: str = "") -> int:
        cur = self.conn.execute("""
            INSERT INTO traces (session_id, provider, model, capability,
                prompt_tokens, input, output, latency_ms, success, error, timestamp)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (session_id, provider, model, capability,
              len(input_text.split()), input_text[:500], output_text[:500],
              latency_ms, int(success), error, datetime.now().isoformat()))
        self.conn.commit()
        return cur.lastrowid

    def recent(self, n: int = 10) -> list:
        rows = self.conn.execute("""
            SELECT provider, model, capability, latency_ms, success, timestamp
            FROM traces ORDER BY id DESC LIMIT ?
        """, (n,)).fetchall()
        return [{"provider": r[0], "model": r[1], "capability": r[2],
                 "latency_ms": r[3], "success": bool(r[4]), "timestamp": r[5][:16]} for r in rows]

    def metrics(self) -> dict:
        rows = self.conn.execute("""
            SELECT provider, model,
                COUNT(*) as total,
                SUM(success) as successes,
                AVG(latency_ms) as avg_latency
            FROM traces GROUP BY provider, model ORDER BY total DESC
        """).fetchall()
        return [{"provider": r[0], "model": r[1], "total": r[2],
                 "success_rate": f"{r[3]/r[2]*100:.0f}%" if r[2] else "0%",
                 "avg_latency_ms": round(r[4] or 0, 1)} for r in rows]
