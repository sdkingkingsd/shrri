"""
Experiments — SHRRI Phase 12
A/B test different prompts, providers, or strategies.
"""
import sqlite3, os, json
from datetime import datetime

DB_PATH = os.path.expanduser("~/.shrri/experiments.db")


class Experiments:
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
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                variants TEXT,
                active INTEGER DEFAULT 1,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS experiment_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_name TEXT,
                variant TEXT,
                score REAL,
                output TEXT,
                timestamp TEXT
            );
        """)
        self.conn.commit()

    def create(self, name: str, variants: dict) -> int:
        try:
            cur = self.conn.execute(
                "INSERT INTO experiments (name, variants, created_at) VALUES (?,?,?)",
                (name, json.dumps(variants), datetime.now().isoformat())
            )
            self.conn.commit()
            return cur.lastrowid
        except Exception:
            return -1

    def run(self, name: str, input_text: str) -> dict:
        row = self.conn.execute(
            "SELECT variants FROM experiments WHERE name=? AND active=1", (name,)
        ).fetchone()
        if not row:
            return {"error": f"Experiment '{name}' not found"}

        variants = json.loads(row[0])
        from engine.router import Router
        r = Router()
        results = {}
        for variant_name, prompt_template in variants.items():
            prompt = prompt_template.replace("{input}", input_text)
            try:
                output = r.chat(prompt, task="fast", web_search=False)
                results[variant_name] = output[:200]
                self.conn.execute(
                    "INSERT INTO experiment_results (experiment_name, variant, score, output, timestamp) VALUES (?,?,?,?,?)",
                    (name, variant_name, 0.0, output[:200], datetime.now().isoformat())
                )
            except Exception as e:
                results[variant_name] = f"ERROR: {e}"
        self.conn.commit()
        return results

    def list_all(self) -> list:
        rows = self.conn.execute(
            "SELECT name, active, created_at FROM experiments ORDER BY id DESC"
        ).fetchall()
        return [{"name": r[0], "active": bool(r[1]), "created": r[2][:10]} for r in rows]
