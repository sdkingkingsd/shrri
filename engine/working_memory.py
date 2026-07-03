"""
Working Memory — SHRRI Phase 9
In-session scratch space: clears when session ends.
Separate from long-term Memory (SQLite facts).
"""
import threading
from datetime import datetime


class WorkingMemory:
    """
    Per-session in-memory store. Thread-safe.
    Keys expire at session end (process lifetime by default).
    Use for: current task context, intermediate results, active goals.
    """
    _sessions: dict = {}
    _lock = threading.Lock()

    @classmethod
    def for_session(cls, session_id: str) -> "WorkingMemory":
        with cls._lock:
            if session_id not in cls._sessions:
                cls._sessions[session_id] = cls(session_id)
            return cls._sessions[session_id]

    @classmethod
    def clear_session(cls, session_id: str):
        with cls._lock:
            cls._sessions.pop(session_id, None)

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._store: dict = {}
        self._lock = threading.Lock()
        self.created_at = datetime.now().isoformat()

    def set(self, key: str, value):
        with self._lock:
            self._store[key] = {"value": value, "set_at": datetime.now().isoformat()}

    def get(self, key: str, default=None):
        with self._lock:
            entry = self._store.get(key)
            return entry["value"] if entry else default

    def delete(self, key: str):
        with self._lock:
            self._store.pop(key, None)

    def all(self) -> dict:
        with self._lock:
            return {k: v["value"] for k, v in self._store.items()}

    def clear(self):
        with self._lock:
            self._store.clear()

    def summary(self) -> str:
        with self._lock:
            if not self._store:
                return "Working memory: empty"
            lines = [f"Working memory ({len(self._store)} items):"]
            for k, v in self._store.items():
                val = str(v["value"])[:80]
                lines.append(f"  {k}: {val}")
            return "\n".join(lines)
