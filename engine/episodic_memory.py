"""
Episodic Memory — SHRRI Phase 9
Stores specific events/experiences with context (what happened, when, where, outcome).
Episodic = "I did X at time T" (autobiographical).
Semantic = "facts about the world" (already in memory.py facts table).
"""
import sqlite3, os, threading
from datetime import datetime

DB_PATH = os.path.expanduser("~/.shrri/episodic.db")


class EpisodicMemory:
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
        self._initialized = True

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                summary TEXT,
                context TEXT,
                outcome TEXT,
                emotion TEXT,
                importance INTEGER DEFAULT 5,
                timestamp TEXT,
                session_id TEXT
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS episodes_fts
            USING fts5(summary, context, outcome, content=episodes);
            CREATE TABLE IF NOT EXISTS experience_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill TEXT,
                what_worked TEXT,
                what_failed TEXT,
                lesson TEXT,
                timestamp TEXT,
                use_count INTEGER DEFAULT 1
            );
        """)
        self.conn.commit()

    def record_episode(self, event_type: str, summary: str, context: str = "",
                       outcome: str = "", emotion: str = "neutral",
                       importance: int = 5, session_id: str = "") -> int:
        now = datetime.now().isoformat()
        cur = self.conn.execute("""
            INSERT INTO episodes (event_type, summary, context, outcome, emotion, importance, timestamp, session_id)
            VALUES (?,?,?,?,?,?,?,?)
        """, (event_type, summary, context, outcome, emotion, importance, now, session_id))
        self.conn.commit()
        # Sync FTS
        rowid = cur.lastrowid
        self.conn.execute(
            "INSERT INTO episodes_fts(rowid, summary, context, outcome) VALUES (?,?,?,?)",
            (rowid, summary, context, outcome)
        )
        self.conn.commit()
        return rowid

    def record_experience(self, skill: str, what_worked: str = "",
                          what_failed: str = "", lesson: str = "") -> int:
        now = datetime.now().isoformat()
        # Check if skill experience already exists
        existing = self.conn.execute(
            "SELECT id, use_count FROM experience_memory WHERE skill=?", (skill,)
        ).fetchone()
        if existing:
            self.conn.execute("""
                UPDATE experience_memory
                SET what_worked=?, what_failed=?, lesson=?, timestamp=?, use_count=use_count+1
                WHERE id=?
            """, (what_worked, what_failed, lesson, now, existing[0]))
            self.conn.commit()
            return existing[0]
        cur = self.conn.execute("""
            INSERT INTO experience_memory (skill, what_worked, what_failed, lesson, timestamp)
            VALUES (?,?,?,?,?)
        """, (skill, what_worked, what_failed, lesson, now))
        self.conn.commit()
        return cur.lastrowid

    def search_episodes(self, query: str, n: int = 5) -> list:
        try:
            from engine.memory import Memory
            from engine.memory import _sanitize_fts_query
            safe_q = _sanitize_fts_query(query)
            rows = self.conn.execute("""
                SELECT e.id, e.event_type, e.summary, e.outcome, e.timestamp, e.importance
                FROM episodes e
                WHERE e.rowid IN (
                    SELECT rowid FROM episodes_fts WHERE episodes_fts MATCH ?
                )
                ORDER BY e.importance DESC, e.timestamp DESC LIMIT ?
            """, (safe_q, n)).fetchall()
        except Exception:
            rows = self.conn.execute("""
                SELECT id, event_type, summary, outcome, timestamp, importance
                FROM episodes ORDER BY importance DESC, timestamp DESC LIMIT ?
            """, (n,)).fetchall()
        return [{"id": r[0], "type": r[1], "summary": r[2],
                 "outcome": r[3], "timestamp": r[4], "importance": r[5]} for r in rows]

    def get_recent_episodes(self, n: int = 10) -> list:
        rows = self.conn.execute("""
            SELECT id, event_type, summary, outcome, timestamp, importance
            FROM episodes ORDER BY timestamp DESC LIMIT ?
        """, (n,)).fetchall()
        return [{"id": r[0], "type": r[1], "summary": r[2],
                 "outcome": r[3], "timestamp": r[4], "importance": r[5]} for r in rows]

    def get_experiences(self, skill: str = None) -> list:
        if skill:
            rows = self.conn.execute(
                "SELECT skill, what_worked, what_failed, lesson, use_count FROM experience_memory WHERE skill=?",
                (skill,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT skill, what_worked, what_failed, lesson, use_count FROM experience_memory ORDER BY use_count DESC"
            ).fetchall()
        return [{"skill": r[0], "worked": r[1], "failed": r[2],
                 "lesson": r[3], "use_count": r[4]} for r in rows]

    def summary(self) -> str:
        total = self.conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
        exp = self.conn.execute("SELECT COUNT(*) FROM experience_memory").fetchone()[0]
        recent = self.get_recent_episodes(3)
        lines = [f"Episodic memory: {total} episodes, {exp} skill experiences"]
        for e in recent:
            lines.append(f"  [{e['timestamp'][:10]}] {e['type']}: {e['summary'][:60]}")
        return "\n".join(lines)
