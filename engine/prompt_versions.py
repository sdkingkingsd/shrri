"""
Prompt Versions — SHRRI Phase 12
Version-controls prompts and tracks which version performs best.
"""
import sqlite3, os
from datetime import datetime

DB_PATH = os.path.expanduser("~/.shrri/prompt_versions.db")


class PromptVersions:
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
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                version INTEGER,
                content TEXT,
                score REAL DEFAULT 0,
                use_count INTEGER DEFAULT 0,
                active INTEGER DEFAULT 1,
                created_at TEXT
            );
        """)
        self.conn.commit()

    def save(self, name: str, content: str) -> int:
        # Get current version
        row = self.conn.execute(
            "SELECT MAX(version) FROM prompts WHERE name=?", (name,)
        ).fetchone()
        version = (row[0] or 0) + 1
        # Deactivate old versions
        self.conn.execute("UPDATE prompts SET active=0 WHERE name=?", (name,))
        cur = self.conn.execute(
            "INSERT INTO prompts (name, version, content, created_at) VALUES (?,?,?,?)",
            (name, version, content, datetime.now().isoformat())
        )
        self.conn.commit()
        return version

    def get_active(self, name: str) -> str:
        row = self.conn.execute(
            "SELECT content FROM prompts WHERE name=? AND active=1", (name,)
        ).fetchone()
        return row[0] if row else ""

    def record_score(self, name: str, score: float):
        self.conn.execute("""
            UPDATE prompts SET score=?, use_count=use_count+1
            WHERE name=? AND active=1
        """, (score, name))
        self.conn.commit()

    def history(self, name: str) -> list:
        rows = self.conn.execute(
            "SELECT version, score, use_count, active, created_at FROM prompts WHERE name=? ORDER BY version DESC",
            (name,)
        ).fetchall()
        return [{"version": r[0], "score": r[1], "use_count": r[2],
                 "active": bool(r[3]), "created": r[4][:10]} for r in rows]
