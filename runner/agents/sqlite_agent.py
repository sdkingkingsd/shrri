"""SQLite Agent — SHRRI Phase 7"""
import logging
logger = logging.getLogger(__name__)

class SQLiteAgent:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def run(self, payload: dict) -> str:
        prompt = payload.get("prompt", "")
        if self.verbose:
            logger.info(f"[sqlite_agent] prompt: {prompt!r}")
        from tools.sqlite_tool import sqlite_query
        return sqlite_query(prompt)
