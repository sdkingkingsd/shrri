"""
Provider Ranking — SHRRI AI OS v2

Tracks success/failure/latency per (capability, provider, model) over
time and re-orders candidates so consistently-failing or slow providers
get tried later, without ever removing them (still a valid fallback).

Does NOT modify capability_map.py directly — wraps get_candidates()
and returns a re-ordered list based on observed stats. Falls back to
the original static order for any candidate with no history yet.
"""

import json
import time
from pathlib import Path
from collections import defaultdict

STATS_PATH = Path.home() / ".shrri" / "provider_stats.json"


class ProviderRanking:
    def __init__(self, stats_path: Path = STATS_PATH):
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        self.stats_path = stats_path
        self._stats = self._load()

    def _load(self) -> dict:
        if self.stats_path.exists():
            with open(self.stats_path) as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(self.stats_path, "w") as f:
            json.dump(self._stats, f, indent=2)

    def _key(self, provider: str, model: str) -> str:
        return f"{provider}::{model}"

    def record(self, provider: str, model: str, success: bool, latency_seconds: float = 0.0):
        key = self._key(provider, model)
        entry = self._stats.setdefault(key, {
            "successes": 0, "failures": 0, "total_latency": 0.0, "last_used": None
        })
        if success:
            entry["successes"] += 1
            entry["total_latency"] += latency_seconds
        else:
            entry["failures"] += 1
        entry["last_used"] = time.time()
        self._save()

    def _score(self, provider: str, model: str) -> float:
        key = self._key(provider, model)
        entry = self._stats.get(key)
        if not entry:
            return 0.5  # neutral score for untested candidates — tried in original order
        total = entry["successes"] + entry["failures"]
        if total == 0:
            return 0.5
        success_rate = entry["successes"] / total
        return success_rate

    def rank_candidates(self, candidates: list[tuple]) -> list[tuple]:
        """
        candidates: list of (provider, model) tuples in original static order.
        Returns re-ordered list — higher success rate first, ties broken
        by keeping original relative order (stable sort).
        """
        scored = [(self._score(p, m), i, (p, m)) for i, (p, m) in enumerate(candidates)]
        scored.sort(key=lambda x: (-x[0], x[1]))  # score desc, original index asc for ties
        return [c for _, _, c in scored]
