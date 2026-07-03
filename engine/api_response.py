"""
API Response Format — SHRRI Phase 16
Standardised response envelope for all SHRRI outputs.
"""
from datetime import datetime
from typing import Any


def ok(data: Any, message: str = "", meta: dict = None) -> dict:
    return {
        "status": "ok",
        "message": message,
        "data": data,
        "meta": meta or {},
        "timestamp": datetime.now().isoformat(timespec="seconds")
    }


def error(message: str, code: str = "error", data: Any = None) -> dict:
    return {
        "status": "error",
        "message": message,
        "code": code,
        "data": data,
        "timestamp": datetime.now().isoformat(timespec="seconds")
    }


def stream_chunk(text: str, done: bool = False, meta: dict = None) -> dict:
    return {
        "type": "chunk" if not done else "done",
        "text": text,
        "meta": meta or {}
    }


def format_for_telegram(response: dict) -> str:
    """Convert API response to Telegram-friendly text."""
    if response["status"] == "error":
        return f"❌ Error: {response['message']}"
    data = response.get("data", "")
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        return "\n".join(f"{k}: {v}" for k, v in data.items())
    if isinstance(data, list):
        return "\n".join(f"• {item}" for item in data)
    return str(data)


def format_for_cli(response: dict) -> str:
    """Convert API response to CLI-friendly text."""
    if response["status"] == "error":
        return f"[ERROR] {response['message']}"
    data = response.get("data", "")
    ts = response.get("timestamp", "")
    header = f"[{ts}] " if ts else ""
    if isinstance(data, str):
        return f"{header}{data}"
    import json
    return f"{header}{json.dumps(data, indent=2)}"
