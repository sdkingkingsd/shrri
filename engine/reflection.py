import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.expanduser("~/.shrri/memory.db")


class ReflectionEngine:
    def __init__(self, conn):
        self.conn = conn
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS reflections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                situation TEXT,
                what_went_wrong TEXT,
                correction TEXT,
                learned TEXT,
                timestamp TEXT
            );

            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_phrase TEXT,
                actual_intent TEXT,
                tool TEXT,
                action TEXT,
                success_count INTEGER DEFAULT 1,
                timestamp TEXT
            );

            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT UNIQUE,
                description TEXT,
                example_input TEXT,
                example_output TEXT,
                use_count INTEGER DEFAULT 1,
                timestamp TEXT
            );
        """)
        self.conn.commit()

    def store_correction(self, situation: str, wrong: str, correction: str):
        """Store when user corrects SHRRI."""
        learned = f"When '{situation}', do '{correction}' not '{wrong}'"
        self.conn.execute("""
            INSERT INTO reflections (situation, what_went_wrong, correction, learned, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (situation, wrong, correction, learned, datetime.now().isoformat()))
        self.conn.commit()
        return learned

    def store_pattern(self, user_phrase: str, intent: str, tool: str, action: str):
        """Store a phrase → intent mapping learned from user."""
        existing = self.conn.execute(
            "SELECT id, success_count FROM patterns WHERE user_phrase=? AND tool=?",
            (user_phrase.lower(), tool)
        ).fetchone()

        if existing:
            self.conn.execute(
                "UPDATE patterns SET success_count=? WHERE id=?",
                (existing[1] + 1, existing[0])
            )
        else:
            self.conn.execute("""
                INSERT INTO patterns (user_phrase, actual_intent, tool, action, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (user_phrase.lower(), intent, tool, action, datetime.now().isoformat()))
        self.conn.commit()

    def store_skill(self, name: str, description: str, example_in: str, example_out: str):
        """Store a skill that worked well."""
        existing = self.conn.execute(
            "SELECT id, use_count FROM skills WHERE skill_name=?", (name,)
        ).fetchone()

        if existing:
            self.conn.execute(
                "UPDATE skills SET use_count=? WHERE id=?",
                (existing[1] + 1, existing[0])
            )
        else:
            self.conn.execute("""
                INSERT INTO skills (skill_name, description, example_input, example_output, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (name, description, example_in, example_out, datetime.now().isoformat()))
        self.conn.commit()

    def get_relevant_lessons(self, message: str) -> str:
        """Pull lessons relevant to current message."""
        rows = self.conn.execute(
            "SELECT learned FROM reflections ORDER BY id DESC LIMIT 10"
        ).fetchall()

        patterns = self.conn.execute(
            "SELECT user_phrase, tool, action, success_count FROM patterns ORDER BY success_count DESC LIMIT 10"
        ).fetchall()

        output = ""

        if rows:
            output += "📚 Past lessons:\n"
            for r in rows:
                output += f"  - {r[0]}\n"

        if patterns:
            output += "\n🧠 Learned patterns:\n"
            for p in patterns:
                output += f"  - '{p[0]}' → {p[1]}/{p[2]} (used {p[3]}x)\n"

        return output

    def get_all_lessons(self) -> str:
        """Show everything SHRRI has learned."""
        reflections = self.conn.execute(
            "SELECT situation, learned, timestamp FROM reflections ORDER BY id DESC"
        ).fetchall()

        patterns = self.conn.execute(
            "SELECT user_phrase, tool, action, success_count FROM patterns ORDER BY success_count DESC"
        ).fetchall()

        skills = self.conn.execute(
            "SELECT skill_name, description, use_count FROM skills ORDER BY use_count DESC"
        ).fetchall()

        out = "\n==== SHRRI LEARNED SO FAR ====\n"

        out += f"\n📝 Corrections ({len(reflections)}):\n"
        for r in reflections:
            out += f"  [{r[2][:10]}] {r[1]}\n"

        out += f"\n🧠 Patterns ({len(patterns)}):\n"
        for p in patterns:
            out += f"  '{p[0]}' → {p[1]}/{p[2]} ({p[3]}x)\n"

        out += f"\n⚡ Skills ({len(skills)}):\n"
        for s in skills:
            out += f"  {s[0]}: {s[1]} ({s[2]}x)\n"

        return out
