import sqlite3
import os
import tempfile
import shutil
from datetime import datetime

DB_PATH = os.environ.get("SHRRI_MEMORY_DB_OVERRIDE") or os.path.expanduser("~/.shrri/memory.db")
DB_ENC_PATH = DB_PATH + ".enc"


class Memory:
    def __init__(self):
        self.tmp_db = None
        self.conn = self._open_db()
        self._init_tables()

    def _open_db(self):
        """Open DB — decrypt if encrypted, else use plain."""
        if os.path.exists(DB_ENC_PATH):
            from .crypto import load_key, decrypt_file
            fernet = load_key()
            data = decrypt_file(DB_PATH, fernet)

            # Write to temp file in /tmp (RAM-backed on Linux)
            tmp = tempfile.NamedTemporaryFile(
                suffix=".db", delete=False, dir="/tmp"
            )
            tmp.write(data)
            tmp.close()
            self.tmp_db = tmp.name
            return sqlite3.connect(self.tmp_db)

        # Plain DB fallback
        return sqlite3.connect(DB_PATH)

    def _save_encrypted(self):
        """Re-encrypt DB from temp file back to disk."""
        if not self.tmp_db or not os.path.exists(self.tmp_db):
            return
        try:
            from .crypto import load_key, encrypt_file
            # Copy temp db to DB_PATH first, then encrypt
            shutil.copy2(self.tmp_db, DB_PATH)
            fernet = load_key()
            encrypt_file(DB_PATH, fernet)
        except Exception as e:
            print(f"[SHRRI] Warning: Could not re-encrypt memory: {e}")

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS fact_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT,
                old_value TEXT,
                new_value TEXT,
                changed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                content TEXT,
                timestamp TEXT
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts
            USING fts5(role, content, content=conversations);
        """)
        self.conn.commit()

    def _scan_injection(self, key, value):
        """Block prompt injection, exfiltration, and junk before saving."""
        import re
        # Block invisible unicode characters
        if any(ord(ch) in range(0x200B, 0x200F) or ord(ch) in range(0x202A, 0x202F) for ch in value):
            return False, "invisible unicode detected"
        # Block prompt injection patterns
        injection_patterns = [
            r"ignore (all |previous |above )?instructions",
            r"system prompt",
            r"you are now",
            r"disregard (all )?previous",
            r"forget (everything|all)",
            r"new personality",
            r"act as (a |an )?",
            r"jailbreak",
            r"do anything now",
        ]
        for pattern in injection_patterns:
            if re.search(pattern, value.lower()):
                return False, f"injection pattern: {pattern}"
        # Block credential exfiltration patterns
        exfil_patterns = [
            r"(send|email|post|upload|exfiltrate).{0,30}(password|key|token|secret|credential)",
            r"curl.{0,50}http",
            r"wget.{0,50}http",
            r"ssh.{0,30}@",
            r"api[_-]?key\s*=",
        ]
        for pattern in exfil_patterns:
            if re.search(pattern, value.lower()):
                return False, f"exfiltration pattern: {pattern}"
        # Block junk keys
        junk_keys = {"ai", "type", "creator_s_name", "none", "null", "undefined"}
        if key.lower().strip() in junk_keys:
            return False, f"junk key: {key}"
        # Block very short/meaningless values
        if len(value.strip()) < 2:
            return False, "value too short"
        # Block values that are just punctuation or numbers only
        if re.match(r"^[\d\s\.\,\!\?\-]+$", value.strip()):
            return False, "numeric/punctuation only value"
        # Block excessively long values (likely tool output, not a fact)
        if len(value) > 300:
            return False, "value too long (likely tool output)"
        return True, "ok"

    def save_fact(self, key, value):
        # Injection scan — block before saving
        ok, reason = self._scan_injection(key, value)
        if not ok:
            print(f"[memory] blocked fact '{key}': {reason}")
            return False
        now = datetime.now().isoformat()
        existing = self.conn.execute(
            "SELECT value FROM facts WHERE key=?", (key,)
        ).fetchone()
        if existing and existing[0] != value:
            self.conn.execute(
                "INSERT INTO fact_history (key, old_value, new_value, changed_at) VALUES (?, ?, ?, ?)",
                (key, existing[0], value, now)
            )
        self.conn.execute("""
            INSERT INTO facts (key, value, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
        """, (key, value, now, now))
        self.conn.commit()
        self._save_encrypted()

    def get_fact(self, key):
        row = self.conn.execute(
            "SELECT value FROM facts WHERE key=?", (key,)
        ).fetchone()
        return row[0] if row else None

    def get_all_facts(self):
        rows = self.conn.execute(
            "SELECT key, value FROM facts"
        ).fetchall()
        return {r[0]: r[1] for r in rows}

    def get_fact_history(self, key=None):
        if key:
            rows = self.conn.execute(
                "SELECT key, old_value, new_value, changed_at FROM fact_history WHERE key=? ORDER BY changed_at DESC LIMIT 10",
                (key,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT key, old_value, new_value, changed_at FROM fact_history ORDER BY changed_at DESC LIMIT 20"
            ).fetchall()
        return [{"key": r[0], "old": r[1], "new": r[2], "when": r[3]} for r in rows]

    def delete_fact(self, key):
        self.conn.execute("DELETE FROM facts WHERE key=?", (key,))
        self.conn.commit()
        self._save_encrypted()

    def save_message(self, role, content):
        self.conn.execute(
            "INSERT INTO conversations (role, content, timestamp) VALUES (?, ?, ?)",
            (role, content, datetime.now().isoformat())
        )
        self.conn.commit()
        self._save_encrypted()

    def get_history(self, limit=20):
        rows = self.conn.execute(
            "SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    def search(self, query):
        rows = self.conn.execute(
            "SELECT role, content FROM conversations_fts WHERE conversations_fts MATCH ? LIMIT 5",
            (query,)
        ).fetchall()
        return [{"role": r[0], "content": r[1]} for r in rows]


    def compress(self, summary: str):
        """Replace all history with a single summary message."""
        self.conn.execute("DELETE FROM conversations")
        self.conn.execute(
            "INSERT INTO conversations (role, content, timestamp) VALUES (?, ?, datetime('now'))",
            ("system", f"[Conversation summary]: {summary}")
        )
        self.conn.commit()
        self._save_encrypted()
    def clear_history(self):
        self.conn.execute("DELETE FROM conversations")
        self.conn.commit()
        self._save_encrypted()

    def close(self):
        """Close connection and clean up temp file."""
        self.conn.close()
        if self.tmp_db and os.path.exists(self.tmp_db):
            os.remove(self.tmp_db)
