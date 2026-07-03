"""
SharedContext — SHRRI Phase 6F
Cross-workflow persistent shared context. Unlike Scratchpad (in-memory,
per-workflow), SharedContext survives restarts and is readable across
multiple /goal runs and sessions.

Three namespaces:
  "global"   — persists forever (facts, preferences, long-term state)
  "session"  — scoped to a Telegram/WhatsApp session_id
  "workflow" — scoped to a workflow_id (auto-expires after 24h)

Backed by SQLite at ~/.shrri/shared_context.db
Thread-safe. Agents access it via payload["shared_context"].

API:
    sc = SharedContext()
    sc.set("global", "user_name", "Sd")
    sc.get("global", "user_name")          # → "Sd"
    sc.all("global")                        # → {"user_name": "Sd", ...}
    sc.delete("global", "user_name")
    sc.cleanup_expired()                    # remove old workflow entries
"""

import sqlite3
import threading
import logging
import json
import time
import os

logger = logging.getLogger(__name__)

DB_PATH = os.path.expanduser("~/.shrri/shared_context.db")
WORKFLOW_TTL = 60 * 60 * 24  # 24 hours in seconds


class SharedContext:
    def __init__(self, db_path: str = DB_PATH):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self):
        with self._lock:
            with self._conn() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS shared_context (
                        namespace TEXT NOT NULL,
                        scope     TEXT NOT NULL,
                        key       TEXT NOT NULL,
                        value     TEXT NOT NULL,
                        updated_at REAL NOT NULL,
                        PRIMARY KEY (namespace, scope, key)
                    )
                """)
                conn.commit()
        logger.debug("[shared_context] DB initialised")

    def set(self, namespace: str, key: str, value,
            scope: str = "") -> None:
        """
        Store a value.
        namespace: "global" | "session" | "workflow"
        scope:     session_id or workflow_id (empty for global)
        """
        serialized = json.dumps(value)
        now = time.time()
        with self._lock:
            with self._conn() as conn:
                conn.execute("""
                    INSERT INTO shared_context
                        (namespace, scope, key, value, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(namespace, scope, key)
                    DO UPDATE SET value=excluded.value,
                                  updated_at=excluded.updated_at
                """, (namespace, scope, key, serialized, now))
                conn.commit()
        logger.debug(f"[shared_context] set {namespace}/{scope}/{key}")

    def get(self, namespace: str, key: str,
            scope: str = "", default=None):
        """Retrieve a value. Returns default if not found."""
        with self._lock:
            with self._conn() as conn:
                row = conn.execute("""
                    SELECT value FROM shared_context
                    WHERE namespace=? AND scope=? AND key=?
                """, (namespace, scope, key)).fetchone()
        if row is None:
            return default
        return json.loads(row[0])

    def all(self, namespace: str, scope: str = "") -> dict:
        """Return all key-value pairs for a namespace+scope."""
        with self._lock:
            with self._conn() as conn:
                rows = conn.execute("""
                    SELECT key, value FROM shared_context
                    WHERE namespace=? AND scope=?
                """, (namespace, scope)).fetchall()
        return {k: json.loads(v) for k, v in rows}

    def delete(self, namespace: str, key: str,
               scope: str = "") -> None:
        with self._lock:
            with self._conn() as conn:
                conn.execute("""
                    DELETE FROM shared_context
                    WHERE namespace=? AND scope=? AND key=?
                """, (namespace, scope, key))
                conn.commit()
        logger.debug(f"[shared_context] deleted {namespace}/{scope}/{key}")

    def cleanup_expired(self) -> int:
        """Remove workflow-scoped entries older than WORKFLOW_TTL. Returns count."""
        cutoff = time.time() - WORKFLOW_TTL
        with self._lock:
            with self._conn() as conn:
                cur = conn.execute("""
                    DELETE FROM shared_context
                    WHERE namespace='workflow' AND updated_at < ?
                """, (cutoff,))
                conn.commit()
                count = cur.rowcount
        if count:
            logger.info(f"[shared_context] cleaned up {count} expired workflow entries")
        return count

    def summary(self) -> str:
        """Human-readable summary of all stored context (for debugging)."""
        with self._lock:
            with self._conn() as conn:
                rows = conn.execute("""
                    SELECT namespace, scope, key, value, updated_at
                    FROM shared_context
                    ORDER BY namespace, scope, key
                """).fetchall()
        if not rows:
            return "[shared_context] empty"
        lines = ["[shared_context] contents:"]
        for ns, sc, k, v, ts in rows:
            scope_str = f"/{sc}" if sc else ""
            lines.append(f"  {ns}{scope_str}/{k} = {v[:60]}")
        return "\n".join(lines)
