"""
Daily Session Log — SHRRI Phase 9
Persists every session's turns to a daily log file + SQLite.
Survives restarts. Browsable by date.
"""
import sqlite3, os, json
from datetime import datetime

DB_PATH = os.path.expanduser("~/.shrri/session_log.db")
LOG_DIR = os.path.expanduser("~/.shrri/logs")


class SessionLog:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        os.makedirs(LOG_DIR, exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._init_tables()
        self._initialized = True

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS session_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                date TEXT,
                role TEXT,
                content TEXT,
                tool TEXT,
                timestamp TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_date ON session_turns(date);
            CREATE INDEX IF NOT EXISTS idx_session ON session_turns(session_id);
        """)
        self.conn.commit()

    def log(self, session_id: str, role: str, content: str, tool: str = ""):
        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        ts = now.isoformat()
        self.conn.execute(
            "INSERT INTO session_turns (session_id, date, role, content, tool, timestamp) VALUES (?,?,?,?,?,?)",
            (session_id, date, role, content[:2000], tool, ts)
        )
        self.conn.commit()
        # Also append to daily flat log file
        log_file = os.path.join(LOG_DIR, f"{date}.log")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] [{session_id[:8]}] {role}: {content[:200]}\n")

    def get_by_date(self, date: str) -> list:
        rows = self.conn.execute("""
            SELECT session_id, role, content, tool, timestamp
            FROM session_turns WHERE date=?
            ORDER BY timestamp ASC
        """, (date,)).fetchall()
        return [{"session": r[0][:8], "role": r[1], "content": r[2],
                 "tool": r[3], "timestamp": r[4]} for r in rows]

    def get_dates(self) -> list:
        rows = self.conn.execute(
            "SELECT DISTINCT date FROM session_turns ORDER BY date DESC"
        ).fetchall()
        return [r[0] for r in rows]

    def today_summary(self) -> str:
        date = datetime.now().strftime("%Y-%m-%d")
        turns = self.get_by_date(date)
        if not turns:
            return f"No session log for {date} yet."
        user_turns = [t for t in turns if t["role"] == "user"]
        tools_used = list({t["tool"] for t in turns if t["tool"]})
        return (
            f"Session log {date}: {len(turns)} turns, "
            f"{len(user_turns)} user messages, "
            f"tools used: {', '.join(tools_used) or 'none'}"
        )
