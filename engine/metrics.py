"""
Metrics — SHRRI Phase 12
Aggregates system-wide performance metrics.
"""
import json, os
from datetime import datetime, timedelta
from pathlib import Path

STATS_PATH = Path.home() / ".shrri" / "provider_stats.json"


def get_provider_metrics() -> dict:
    if not STATS_PATH.exists():
        return {}
    with open(STATS_PATH) as f:
        stats = json.load(f)
    result = {}
    for key, entry in stats.items():
        provider, model = key.split("::", 1)
        total = entry["successes"] + entry["failures"]
        avg_lat = (entry["total_latency"] / entry["successes"]) if entry["successes"] else 0
        result[key] = {
            "provider": provider, "model": model,
            "total_calls": total,
            "success_rate": f"{entry['successes']/total*100:.0f}%" if total else "0%",
            "avg_latency_s": round(avg_lat, 2)
        }
    return result


def get_benchmark_metrics() -> dict:
    try:
        from engine.self_benchmark import SelfBenchmark
        sb = SelfBenchmark()
        history = sb.history(5)
        return {"recent_runs": history}
    except Exception as e:
        return {"error": str(e)}


def get_tool_usage_metrics() -> dict:
    try:
        import sqlite3
        conn = sqlite3.connect(os.path.expanduser("~/.shrri/session_log.db"))
        rows = conn.execute("""
            SELECT tool, COUNT(*) as count FROM session_turns
            WHERE tool != '' GROUP BY tool ORDER BY count DESC LIMIT 10
        """).fetchall()
        conn.close()
        return {r[0]: r[1] for r in rows}
    except Exception:
        return {}


def full_metrics_report() -> str:
    lines = ["📊 SHRRI Metrics Report", "=" * 40]

    provider_m = get_provider_metrics()
    lines.append(f"\n🔌 Provider Performance ({len(provider_m)} providers):")
    for key, m in list(provider_m.items())[:5]:
        lines.append(f"  {m['provider']}/{m['model']}: {m['total_calls']} calls, "
                     f"{m['success_rate']} success, {m['avg_latency_s']}s avg")

    bench_m = get_benchmark_metrics()
    if "recent_runs" in bench_m:
        lines.append(f"\n🧪 Benchmark History:")
        for run in bench_m["recent_runs"]:
            lines.append(f"  [{run['timestamp']}] {run['passed']}/{run['total']} ({run['score']})")

    tool_m = get_tool_usage_metrics()
    if tool_m:
        lines.append(f"\n🔧 Top Tools Used:")
        for tool, count in list(tool_m.items())[:5]:
            lines.append(f"  {tool}: {count}x")

    return "\n".join(lines)
