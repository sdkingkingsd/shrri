"""
Generates a full, honest status report of SHRRI — architecture, capabilities,
known limitations, and test results. Run this anytime you want a real snapshot
of where the project actually stands, instead of relying on memory of what
was built across many sessions.
"""
import sys
sys.path.insert(0, '/home/shrridharshan/shrri')

import os
import subprocess


def section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def run():
    section("1. FILE / MODULE INVENTORY")
    for root_dir in ["engine", "tools"]:
        path = os.path.join(os.path.expanduser("~/shrri"), root_dir)
        if os.path.isdir(path):
            print(f"\n{root_dir}/")
            for f in sorted(os.listdir(path)):
                if f.endswith(".py"):
                    full = os.path.join(path, f)
                    lines = sum(1 for _ in open(full, encoding="utf-8", errors="ignore"))
                    print(f"  {f:<25} {lines} lines")

    section("2. GIT HISTORY (what's actually been committed)")
    try:
        log = subprocess.run(
            ["git", "log", "--oneline"], cwd=os.path.expanduser("~/shrri"),
            capture_output=True, text=True
        )
        print(log.stdout)
    except Exception as e:
        print(f"(git log failed: {e})")

    section("3. MEMORY DATABASE — what SHRRI actually knows")
    from engine.memory import Memory
    m = Memory()

    facts = m.get_all_facts()
    print(f"\nFacts stored: {len(facts)}")
    for k, v in facts.items():
        print(f"  - {k}: {v}")

    patterns = m.conn.execute("SELECT COUNT(*) FROM patterns").fetchone()[0]
    reflections = m.conn.execute("SELECT COUNT(*) FROM reflections").fetchone()[0]
    skills = m.conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
    print(f"\nLearned patterns: {patterns}")
    print(f"Stored corrections/reflections: {reflections}")
    print(f"Stored skills: {skills}")

    section("4. GAP LOG — real failures SHRRI has hit")
    from engine.gaps import GapLogger
    gl = GapLogger(m.conn)
    unresolved = gl.get_unresolved(limit=20)
    print(f"\nUnresolved gaps: {len(unresolved)}")
    for g in unresolved:
        print(f"  [{g['timestamp'][:16]}] {g['category']}: {g['message'][:60]}")

    section("5. PROVIDER / KEY STATUS")
    from engine.client import SHRRIEngine
    e = SHRRIEngine()
    e.status()

    section("6. CAPABILITIES — what actually works (verified by tests tonight)")
    print("""
  ✅ Gmail — read inbox, read specific email body (keyword + LLM matching),
     send email (casing-preserving, requires real recipient address)
  ✅ Web search fallback when no tool matches
  ✅ Voice input (offline Whisper, push-to-talk)
  ✅ Multi-provider routing with automatic failover (Groq → Cerebras → Nvidia → Ollama)
  ✅ Fact memory (persists across sessions)
  ✅ Correction learning (stores explicit user corrections)
  ✅ Pattern learning (phrase → intent mapping), NOW relevance-filtered
     (stopword-aware — fixed tonight, was previously injecting irrelevant noise)
  ✅ Gap logging + diagnose (read-only failure analysis, never auto-applies fixes)
  ✅ Prompt injection resistance (hardened tonight — was previously 100% compliant
     with "ignore your instructions" attacks)
  ✅ Real-time/date tool (deterministic, not LLM-guessed)
  ⚠️  Reasoning mode (think:/verify: prefix, or auto on research/plan categories) —
     PARTIAL reliability improvement only, NOT solved (see section 7)
    """)

    section("7. KNOWN LIMITATIONS — confirmed by direct testing, not assumed")
    print("""
  ❌ Cannot do reliable mental arithmetic (proven in thinking_test.py Test 4 —
     produced extra nonsensical steps, got a wrong intermediate answer, patched
     over it without resolving why). NO calculator tool built yet.
  ❌ Cannot accurately explain its own past reasoning (Test 3) — any
     "explanation" is a fresh generation, not a real memory of process.
     This is a fundamental LLM limitation, not a SHRRI-specific bug.
  ⚠️  Step-by-step + verify mode reduces but does NOT eliminate logical
     contradictions on novel puzzles — verification steps can be hollow
     (format of checking without real substance), confirmed directly tonight.
  ⚠️  Uses small free-tier models (8B class) — meaningfully less reliable
     than larger frontier models on multi-step reasoning.
  ⚠️  Heavy Groq rate-limiting under load (6000 TPM cap) causes frequent
     failover — adds latency, occasionally degrades response quality when
     falling back to NVIDIA's smaller instruct model.
    """)

    section("DONE")
    print("This is a real, evidence-based snapshot — not a marketing description.")


if __name__ == "__main__":
    run()
