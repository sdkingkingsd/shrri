"""
Structured Logs — SHRRI Phase 16
JSON-structured logging for all SHRRI subsystems.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from enum import Enum

LOG_DIR = Path.home() / ".shrri" / "logs"
LOG_PATH = LOG_DIR / "shrri.jsonl"


class Level(str, Enum):
    DEBUG = "DEBUG"
    INFO  = "INFO"
    WARN  = "WARN"
    ERROR = "ERROR"


class StructuredLogger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self._log_path = LOG_PATH
        self._console = True   # also print to stderr
        self._initialized = True

    def _write(self, level: str, component: str, message: str, data: dict = None):
        entry = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "level": level,
            "component": component,
            "msg": message,
        }
        if data:
            entry["data"] = data
        line = json.dumps(entry)
        with open(self._log_path, "a") as f:
            f.write(line + "\n")
        if self._console and level in ("WARN", "ERROR"):
            icon = {"WARN": "⚠️", "ERROR": "❌"}.get(level, "")
            print(f"{icon} [{level}] {component}: {message}", file=sys.stderr)

    def debug(self, component: str, msg: str, data: dict = None):
        self._write(Level.DEBUG, component, msg, data)

    def info(self, component: str, msg: str, data: dict = None):
        self._write(Level.INFO, component, msg, data)

    def warn(self, component: str, msg: str, data: dict = None):
        self._write(Level.WARN, component, msg, data)

    def error(self, component: str, msg: str, data: dict = None):
        self._write(Level.ERROR, component, msg, data)

    def tail(self, n: int = 20, level: str = None) -> list:
        if not self._log_path.exists():
            return []
        lines = self._log_path.read_text().splitlines()
        entries = [json.loads(l) for l in lines if l.strip()]
        if level:
            entries = [e for e in entries if e.get("level") == level.upper()]
        return entries[-n:]

    def tail_str(self, n: int = 20, level: str = None) -> str:
        entries = self.tail(n, level)
        if not entries:
            return "(no log entries)"
        lines = []
        for e in entries:
            icon = {"DEBUG": "🔍", "INFO": "ℹ️", "WARN": "⚠️", "ERROR": "❌"}.get(e["level"], "")
            lines.append(f"{icon} [{e['ts']}] {e['component']}: {e['msg']}")
        return "\n".join(lines)


# Module-level convenience
_log = StructuredLogger()
debug = _log.debug
info  = _log.info
warn  = _log.warn
error = _log.error
tail  = _log.tail
tail_str = _log.tail_str
