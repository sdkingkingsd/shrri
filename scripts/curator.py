#!/usr/bin/env python3
"""
SHRRI Autonomous Curator
Inspired by Hermes' Curator agent
Grades, prunes, and consolidates facts DB autonomously
"""
import sys, os, json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/home/shrridharshan/shrri')
from engine.memory import Memory
from engine.router import Router as LLMRouter

DREAMS_FILE = Path.home() / ".shrri" / "DREAMS.md"

def run_curator():
    print(f"[curator] Starting at {datetime.now()}")
    m = Memory()
    facts = m.get_all_facts()

    if not facts:
        print("[curator] No facts to curate")
        return

    print(f"[curator] Grading {len(facts)} facts...")

    # Build facts list for LLM grading
    facts_text = "\n".join([f"- {k}: {v}" for k, v in facts.items()])

    grade_prompt = f"""You are SHRRI's memory curator. Grade these facts about Shrridharshan.

Facts to review:
{facts_text}

For each fact, decide:
- KEEP: useful, accurate, worth remembering
- UPDATE: useful but needs cleaning (provide clean version)
- DELETE: junk, duplicate, test data, or meaningless

Rules:
- Keys like "dream_what_do_you_know", "dream_what_is_my" are test queries — DELETE them
- Keys starting with "note_" that have been properly extracted — DELETE if duplicate
- Personal facts (name, college, food, wake time) — KEEP
- Vague or meaningless facts — DELETE

Respond ONLY with valid JSON:
{{"actions": [
  {{"key": "fact_key", "action": "KEEP"}},
  {{"key": "fact_key", "action": "DELETE"}},
  {{"key": "fact_key", "action": "UPDATE", "new_value": "cleaner value"}}
]}}"""

    try:
        router = LLMRouter()
        raw = router.chat(grade_prompt, task="fast", web_search=False)
        raw = raw.strip()
        # Strip markdown fences
        import re
        raw = re.sub(r"^```json|```$", "", raw, flags=re.MULTILINE).strip()
        data = json.loads(raw)
        actions = data.get("actions", [])
    except Exception as e:
        print(f"[curator] LLM grading failed: {e}")
        return

    kept, deleted, updated = 0, 0, 0

    for action in actions:
        key = action.get("key", "")
        act = action.get("action", "KEEP")

        if not key or key not in facts:
            continue

        if act == "DELETE":
            m.delete_fact(key)
            print(f"[curator] Deleted: {key}")
            deleted += 1
        elif act == "UPDATE":
            new_val = action.get("new_value", "")
            if new_val:
                m.save_fact(key, new_val)
                print(f"[curator] Updated: {key} -> {new_val}")
                updated += 1
        else:
            kept += 1

    m._save_encrypted()

    # Write to DREAMS.md
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(DREAMS_FILE, "a") as f:
        f.write(f"\n\n## Curator Run — {now}\n")
        f.write(f"- Facts reviewed: {len(facts)}\n")
        f.write(f"- Kept: {kept}\n")
        f.write(f"- Updated: {updated}\n")
        f.write(f"- Deleted: {deleted}\n")

    print(f"[curator] Done — kept:{kept} updated:{updated} deleted:{deleted}")

if __name__ == "__main__":
    run_curator()
