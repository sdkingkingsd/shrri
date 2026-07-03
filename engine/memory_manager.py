"""
Memory Manager — SHRRI Phase 9
Handles: Ranking, Compression, Forgetting across all memory layers.
"""
import sqlite3, os, threading
from datetime import datetime, timedelta
from engine.memory import Memory
from engine.episodic_memory import EpisodicMemory

FORGETTING_DAYS = 90      # forget low-importance episodes older than this
COMPRESSION_THRESHOLD = 5 # compress when >N episodes of same type exist


class MemoryManager:
    def __init__(self):
        self.long_term = Memory()
        self.episodic = EpisodicMemory()

    # ── Ranking ──
    def rank_facts(self, top_n: int = 10) -> list:
        """Rank long-term facts by recency + access pattern."""
        rows = self.long_term.conn.execute("""
            SELECT key, value, updated_at FROM facts
            ORDER BY updated_at DESC LIMIT ?
        """, (top_n,)).fetchall()
        return [{"key": r[0], "value": r[1], "updated": r[2]} for r in rows]

    def rank_episodes(self, top_n: int = 10) -> list:
        """Rank episodes by importance score."""
        rows = self.episodic.conn.execute("""
            SELECT id, event_type, summary, importance, timestamp
            FROM episodes ORDER BY importance DESC, timestamp DESC LIMIT ?
        """, (top_n,)).fetchall()
        return [{"id": r[0], "type": r[1], "summary": r[2],
                 "importance": r[3], "timestamp": r[4]} for r in rows]

    # ── Compression ──
    def compress_episodes(self, event_type: str = None) -> str:
        """
        When >COMPRESSION_THRESHOLD episodes of same type exist,
        summarize them into one compressed episode using LLM.
        """
        query = "SELECT id, summary, outcome, timestamp FROM episodes"
        args = []
        if event_type:
            query += " WHERE event_type=?"
            args.append(event_type)
        query += " ORDER BY timestamp ASC"
        rows = self.episodic.conn.execute(query, args).fetchall()

        if len(rows) <= COMPRESSION_THRESHOLD:
            return f"No compression needed ({len(rows)} episodes, threshold={COMPRESSION_THRESHOLD})"

        # Group by event_type
        from collections import defaultdict
        groups = defaultdict(list)
        all_rows = self.episodic.conn.execute(
            "SELECT id, event_type, summary, outcome, timestamp FROM episodes ORDER BY timestamp ASC"
        ).fetchall()
        for r in all_rows:
            groups[r[1]].append(r)

        compressed = 0
        for etype, episodes in groups.items():
            if len(episodes) <= COMPRESSION_THRESHOLD:
                continue
            # Summarize with LLM
            summaries = "\n".join(f"- [{e[4][:10]}] {e[2]} → {e[3]}" for e in episodes)
            try:
                from engine.router import Router
                r = Router()
                compressed_text = r.chat(
                    f"Summarize these {len(episodes)} '{etype}' events into one concise paragraph:\n{summaries}",
                    task="fast", web_search=False
                )
            except Exception as e:
                compressed_text = f"[compressed {len(episodes)} events] " + summaries[:200]

            # Delete old, insert compressed
            ids = [e[0] for e in episodes]
            self.episodic.conn.execute(
                f"DELETE FROM episodes WHERE id IN ({','.join('?'*len(ids))})", ids
            )
            self.episodic.record_episode(
                event_type=etype,
                summary=f"[COMPRESSED {len(episodes)} events] " + compressed_text[:300],
                context="auto-compressed by MemoryManager",
                outcome="compressed",
                importance=7
            )
            compressed += len(episodes)

        return f"✅ Compressed {compressed} episodes into summaries"

    # ── Forgetting ──
    def forget_old(self, days: int = FORGETTING_DAYS, min_importance: int = 4) -> str:
        """Delete low-importance episodes older than N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cur = self.episodic.conn.execute("""
            DELETE FROM episodes
            WHERE timestamp < ? AND importance < ?
        """, (cutoff, min_importance))
        self.episodic.conn.commit()
        deleted = cur.rowcount

        # Also forget stale short-term facts
        from engine.short_term_memory import ShortTermMemory
        stm = ShortTermMemory()
        stm._cleanup_expired()

        return f"✅ Forgot {deleted} low-importance episodes older than {days} days"

    def forget_fact(self, key: str) -> str:
        self.long_term.delete_fact(key)
        return f"✅ Forgot fact: {key}"

    # ── Full status ──
    def status(self) -> str:
        facts_count = self.long_term.conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        ep_count = self.episodic.conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
        exp_count = self.episodic.conn.execute("SELECT COUNT(*) FROM experience_memory").fetchone()[0]
        top_facts = self.rank_facts(3)
        top_eps = self.rank_episodes(3)
        lines = [
            f"Memory Status:",
            f"  Long-term facts: {facts_count}",
            f"  Episodes: {ep_count}",
            f"  Skill experiences: {exp_count}",
            f"  Top facts: {', '.join(f['key'] for f in top_facts)}",
            f"  Top episodes: {', '.join(e['summary'][:30] for e in top_eps)}",
        ]
        return "\n".join(lines)
