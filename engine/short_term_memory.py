"""
Short-term Memory — SHRRI Phase 9
Formalized sliding window of recent turns + extracted facts.
Sits between working memory (volatile) and long-term memory (persistent).
Persists to SQLite so it survives restarts but auto-expires after TTL.
"""
import sqlite3, os, threading
from datetime import datetime, timedelta

DB_PATH = os.path.expanduser("~/.shrri/short_term.db")
DEFAULT_TTL_HOURS = 2   # entries expire after 2 hours
MAX_TURNS = 20          # max recent turns to keep per session


class ShortTermMemory:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
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
        self._cleanup_expired()
        self._initialized = True

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                timestamp TEXT,
                expires_at TEXT
            );
            CREATE TABLE IF NOT EXISTS extracted_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                key TEXT,
                value TEXT,
                timestamp TEXT,
                expires_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_facts_session ON extracted_facts(session_id);
        """)
        self.conn.commit()

    def _expires_at(self, hours=DEFAULT_TTL_HOURS) -> str:
        return (datetime.now() + timedelta(hours=hours)).isoformat()

    def _cleanup_expired(self):
        now = datetime.now().isoformat()
        self.conn.execute("DELETE FROM turns WHERE expires_at < ?", (now,))
        self.conn.execute("DELETE FROM extracted_facts WHERE expires_at < ?", (now,))
        self.conn.commit()

    def add_turn(self, session_id: str, role: str, content: str):
        now = datetime.now().isoformat()
        self.conn.execute(
            "INSERT INTO turns (session_id, role, content, timestamp, expires_at) VALUES (?,?,?,?,?)",
            (session_id, role, content[:2000], now, self._expires_at())
        )
        self.conn.commit()
        # Trim to MAX_TURNS per session
        self.conn.execute("""
            DELETE FROM turns WHERE session_id=? AND id NOT IN (
                SELECT id FROM turns WHERE session_id=?
                ORDER BY timestamp DESC LIMIT ?
            )
        """, (session_id, session_id, MAX_TURNS))
        self.conn.commit()

    def get_recent_turns(self, session_id: str, n: int = 10) -> list:
        self._cleanup_expired()
        rows = self.conn.execute("""
            SELECT role, content, timestamp FROM turns
            WHERE session_id=?
            ORDER BY timestamp DESC LIMIT ?
        """, (session_id, n)).fetchall()
        return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in reversed(rows)]

    def save_fact(self, session_id: str, key: str, value: str):
        now = datetime.now().isoformat()
        self.conn.execute("""
            INSERT OR REPLACE INTO extracted_facts (session_id, key, value, timestamp, expires_at)
            VALUES (?,?,?,?,?)
        """, (session_id, key, value, now, self._expires_at(hours=24)))
        self.conn.commit()

    def get_fact(self, session_id: str, key: str) -> str:
        self._cleanup_expired()
        row = self.conn.execute(
            "SELECT value FROM extracted_facts WHERE session_id=? AND key=?",
            (session_id, key)
        ).fetchone()
        return row[0] if row else None

    def get_all_facts(self, session_id: str) -> dict:
        self._cleanup_expired()
        rows = self.conn.execute(
            "SELECT key, value FROM extracted_facts WHERE session_id=?",
            (session_id,)
        ).fetchall()
        return {r[0]: r[1] for r in rows}

    def summary(self, session_id: str) -> str:
        turns = self.get_recent_turns(session_id, 5)
        facts = self.get_all_facts(session_id)
        lines = [f"Short-term memory — session {session_id[:8]}:"]
        lines.append(f"  Recent turns: {len(turns)}")
        if facts:
            lines.append(f"  Facts: {', '.join(f'{k}={v}' for k,v in list(facts.items())[:5])}")
        return "\n".join(lines)
