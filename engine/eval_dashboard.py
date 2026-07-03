"""
Eval Dashboard — SHRRI Phase 12
Unified CLI dashboard for the evaluation system.
"""
from engine.tracer import Tracer
from engine.metrics import get_provider_metrics, get_benchmark_metrics, get_tool_usage_metrics
from engine.prompt_versions import PromptVersions
from engine.experiments import Experiments


def dashboard() -> str:
    lines = ["", "╔══════════════════════════════════════════╗",
             "║     SHRRI Evaluation Dashboard           ║",
             "╚══════════════════════════════════════════╝"]

    # Provider metrics
    pm = get_provider_metrics()
    lines.append(f"\n🔌 Providers ({len(pm)} tracked):")
    for key, m in list(pm.items())[:5]:
        lines.append(f"  {m['provider']}/{m['model']:<28} "
                     f"{m['total_calls']:>3} calls  {m['success_rate']:>4}  {m['avg_latency_s']}s")

    # Tracer recent
    t = Tracer()
    recent = t.recent(5)
    lines.append(f"\n🔍 Recent Traces ({len(recent)}):")
    for r in recent:
        status = "✅" if r["success"] else "❌"
        lines.append(f"  {status} [{r['timestamp']}] {r['provider']}/{r['model']} "
                     f"({r['latency_ms']:.0f}ms) — {r['capability']}")

    # Benchmark history
    bm = get_benchmark_metrics()
    if "recent_runs" in bm and bm["recent_runs"]:
        lines.append(f"\n🧪 Benchmark Runs:")
        for run in bm["recent_runs"]:
            bar = "█" * run["passed"] + "░" * (run["total"] - run["passed"])
            lines.append(f"  [{run['timestamp']}] {bar} {run['score']}")

    # Prompt versions
    pv = PromptVersions()
    rows = pv.conn.execute(
        "SELECT DISTINCT name FROM prompts ORDER BY name"
    ).fetchall()
    if rows:
        lines.append(f"\n📝 Prompt Versions ({len(rows)} prompts):")
        for (name,) in rows:
            hist = pv.history(name)
            active = next((h for h in hist if h["active"]), None)
            if active:
                lines.append(f"  {name}: v{active['version']} "
                             f"score={active['score']} uses={active['use_count']}")

    # Experiments
    ex = Experiments()
    exps = ex.list_all()
    if exps:
        lines.append(f"\n⚗️  Experiments ({len(exps)}):")
        for e in exps:
            status = "🟢" if e["active"] else "⚪"
            lines.append(f"  {status} {e['name']} (created {e['created']})")

    lines.append("\n" + "─" * 44)
    return "\n".join(lines)


if __name__ == "__main__":
    print(dashboard())
