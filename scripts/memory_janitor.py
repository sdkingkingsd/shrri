#!/usr/bin/env python3
import sys, re
sys.path.insert(0, '/home/shrridharshan/shrri')
from engine.memory import Memory

m = Memory()
facts = m.get_all_facts()

# 1. Remove junk keys
junk_keys = {"ai", "creator's_name", "creator_s_name", "type"}
for k in list(facts.keys()):
    if k in junk_keys:
        m.delete_fact(k)
        print(f"[janitor] deleted junk: {k}")

# 2. Consolidate note_ keys
note_patterns = {
    r"wake.?up.*?(\d+\s*(?:am|pm))": "wake_time",
    r"prefer\s+(dark|light)\s+mode": "display_mode",
    r"favourite\s+food\s+is\s+(\w+)": "favourite_food",
    r"born\s+in\s+(\d{4})": "birth_year",
}
for k, v in list(facts.items()):
    if k.startswith("note_"):
        for pattern, clean_key in note_patterns.items():
            match = re.search(pattern, v.lower())
            if match:
                m.save_fact(clean_key, match.group(1))
                m.delete_fact(k)
                print(f"[janitor] consolidated: {k} -> {clean_key}: {match.group(1)}")
                break

# 3. Remove duplicate values
seen_values = {}
for k, v in list(facts.items()):
    if v in seen_values:
        if len(k) > len(seen_values[v]):
            m.delete_fact(k)
            print(f"[janitor] removed duplicate: {k}")
        else:
            m.delete_fact(seen_values[v])
            print(f"[janitor] removed duplicate: {seen_values[v]}")
            seen_values[v] = k
    else:
        seen_values[v] = k

m._save_encrypted()
print("[janitor] done")
