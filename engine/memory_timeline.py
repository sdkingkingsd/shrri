"""
Memory Timeline — SHRRI Phase 9
Browsable chronological view across all memory layers.
"""
from datetime import datetime, timedelta


class MemoryTimeline:
    def __init__(self):
        from engine.memory import Memory
        from engine.episodic_memory import EpisodicMemory
        from engine.session_log import SessionLog
        self.long_term = Memory()
        self.episodic = EpisodicMemory()
        self.session_log = SessionLog()

    def get_timeline(self, days: int = 7) -> list:
        """Return unified chronological events across all memory layers."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        events = []

        # Long-term facts updated recently
        rows = self.long_term.conn.execute(
            "SELECT key, value, updated_at FROM facts WHERE updated_at > ? ORDER BY updated_at DESC",
            (cutoff,)
        ).fetchall()
        for r in rows:
            events.append({"timestamp": r[2], "layer": "long_term",
                           "type": "fact", "summary": f"{r[0]} = {r[1][:50]}"})

        # Episodes
        rows = self.episodic.conn.execute(
            "SELECT event_type, summary, outcome, timestamp, importance FROM episodes WHERE timestamp > ? ORDER BY timestamp DESC",
            (cutoff,)
        ).fetchall()
        for r in rows:
            events.append({"timestamp": r[3], "layer": "episodic",
                           "type": r[0], "summary": r[1][:80],
                           "outcome": r[2], "importance": r[4]})

        # Session log turns (user only, last N days)
        dates = self.session_log.get_dates()
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        for date in dates:
            if date < cutoff_date:
                continue
            turns = self.session_log.get_by_date(date)
            for t in turns:
                if t["role"] == "user":
                    events.append({"timestamp": t["timestamp"], "layer": "session",
                                   "type": "user_message", "summary": t["content"][:80]})

        # Sort chronologically
        events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return events

    def format_timeline(self, days: int = 7) -> str:
        events = self.get_timeline(days)
        if not events:
            return f"No memory events in the last {days} days."
        lines = [f"Memory Timeline — last {days} days ({len(events)} events):"]
        for e in events[:20]:
            ts = e.get("timestamp", "")[:16]
            layer = e.get("layer", "?")
            summary = e.get("summary", "")
            lines.append(f"  [{ts}] [{layer}] {summary}")
        if len(events) > 20:
            lines.append(f"  ... and {len(events)-20} more")
        return "\n".join(lines)
