import sqlite3
import os
import tempfile
import shutil
from datetime import datetime

DB_PATH = os.path.expanduser("~/.shrri/memory.db")
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
                created_at TEXT
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

    def save_fact(self, key, value):
        self.conn.execute("""
            INSERT INTO facts (key, value, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """, (key, value, datetime.now().isoformat()))
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

    def clear_history(self):
        self.conn.execute("DELETE FROM conversations")
        self.conn.commit()
        self._save_encrypted()

    def close(self):
        """Close connection and clean up temp file."""
        self.conn.close()
        if self.tmp_db and os.path.exists(self.tmp_db):
            os.remove(self.tmp_db)
