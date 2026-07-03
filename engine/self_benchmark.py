"""
Self Benchmark — SHRRI Phase 11
Tests SHRRI's own capabilities and tracks performance over time.
"""
import sqlite3, os, json, time
from datetime import datetime

DB_PATH = os.path.expanduser("~/.shrri/benchmarks.db")

BENCHMARK_SUITE = [
    {"id": "math_basic", "type": "math",
     "input": "what is 17 * 23", "expected_contains": "391"},
    {"id": "time_check", "type": "time",
     "input": "what time is it", "expected_contains": None},
    {"id": "memory_recall", "type": "direct",
     "input": "my favourite language", "expected_contains": "python"},
    {"id": "intent_screenshot", "type": "intent",
     "input": "screenshot", "expected_tool": "computer_use"},
    {"id": "intent_email", "type": "intent",
     "input": "check my email", "expected_tool": "gmail"},
]


class SelfBenchmark:
    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                total INTEGER,
                passed INTEGER,
                score REAL
            );
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                benchmark_id TEXT,
                passed INTEGER,
                latency_ms REAL,
                output TEXT,
                timestamp TEXT
            );
        """)
        self.conn.commit()

    def run(self, verbose: bool = True) -> dict:
        from tools.dispatcher import detect_intent, run_tool
        from engine.router import Router

        r = Router()
        passed = 0
        results = []
        run_ts = datetime.now().isoformat()

        for bench in BENCHMARK_SUITE:
            start = time.time()
            try:
                if bench["type"] == "intent":
                    intent = detect_intent(bench["input"])
                    output = intent.get("tool", "")
                    ok = output == bench.get("expected_tool", "")
                elif bench["type"] == "direct":
                    from engine.memory import Memory
                    m = Memory()
                    facts = m.get_all_facts()
                    output = " ".join(str(v) for v in facts.values())
                    expected = bench.get("expected_contains")
                    ok = (expected is None) or (expected.lower() in output.lower())
                elif bench["type"] in ("math", "time", "memory", "memory_search"):
                    intent = detect_intent(bench["input"])
                    output = run_tool(intent, bench["input"])
                    expected = bench.get("expected_contains")
                    ok = (expected is None) or (expected.lower() in output.lower())
                else:
                    output = r.chat(bench["input"], task="fast", web_search=False)
                    expected = bench.get("expected_contains")
                    ok = (expected is None) or (expected.lower() in output.lower())
            except Exception as e:
                output = f"ERROR: {e}"
                ok = False

            latency = (time.time() - start) * 1000
            if ok:
                passed += 1
            results.append({
                "id": bench["id"], "passed": ok,
                "latency_ms": round(latency, 1), "output": str(output)[:100]
            })
            if verbose:
                status = "✅" if ok else "❌"
                print(f"  {status} {bench['id']} ({latency:.0f}ms)")

        score = passed / len(BENCHMARK_SUITE)
        cur = self.conn.execute(
            "INSERT INTO runs (timestamp, total, passed, score) VALUES (?,?,?,?)",
            (run_ts, len(BENCHMARK_SUITE), passed, score)
        )
        run_id = cur.lastrowid
        for res in results:
            self.conn.execute(
                "INSERT INTO results (run_id, benchmark_id, passed, latency_ms, output, timestamp) VALUES (?,?,?,?,?,?)",
                (run_id, res["id"], int(res["passed"]), res["latency_ms"], res["output"], run_ts)
            )
        self.conn.commit()

        return {"passed": passed, "total": len(BENCHMARK_SUITE),
                "score": score, "results": results}

    def history(self, n: int = 5) -> list:
        rows = self.conn.execute(
            "SELECT timestamp, passed, total, score FROM runs ORDER BY id DESC LIMIT ?", (n,)
        ).fetchall()
        return [{"timestamp": r[0][:16], "passed": r[1],
                 "total": r[2], "score": f"{r[3]*100:.0f}%"} for r in rows]
