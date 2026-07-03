"""
Audit Log — SHRRI Phase 13
Immutable append-only log of all security-relevant events.
"""
import sqlite3, os, json
from datetime import datetime

DB_PATH = os.path.expanduser("~/.shrri/audit.db")


class AuditLog:
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
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                actor TEXT,
                action TEXT NOT NULL,
                resource TEXT,
                result TEXT,
                details TEXT
            );
        """)
        self.conn.commit()

    def log(self, action: str, resource: str = "", result: str = "ok",
            actor: str = "system", details: dict = None):
        self.conn.execute(
            "INSERT INTO audit_events (timestamp, actor, action, resource, result, details) VALUES (?,?,?,?,?,?)",
            (datetime.now().isoformat(), actor, action, resource, result,
             json.dumps(details or {}))
        )
        self.conn.commit()

    def recent(self, n: int = 20) -> list:
        rows = self.conn.execute(
            "SELECT timestamp, actor, action, resource, result FROM audit_events ORDER BY id DESC LIMIT ?",
            (n,)
        ).fetchall()
        return [{"timestamp": r[0][:19], "actor": r[1], "action": r[2],
                 "resource": r[3], "result": r[4]} for r in rows]

    def query(self, action: str = None, result: str = None, n: int = 50) -> list:
        where, params = [], []
        if action:
            where.append("action=?"); params.append(action)
        if result:
            where.append("result=?"); params.append(result)
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        params.append(n)
        rows = self.conn.execute(
            f"SELECT timestamp, actor, action, resource, result FROM audit_events {clause} ORDER BY id DESC LIMIT ?",
            params
        ).fetchall()
        return [{"timestamp": r[0][:19], "actor": r[1], "action": r[2],
                 "resource": r[3], "result": r[4]} for r in rows]
