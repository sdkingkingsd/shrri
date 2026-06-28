#!/usr/bin/env python3
"""
SHRRI Weekly Consolidator
Every Sunday — reads last 7 days of notes, extracts key facts, updates facts DB
"""
import sys, os, sqlite3
from datetime import datetime, timedelta
sys.path.insert(0, '/home/shrridharshan/shrri')
from engine.memory import Memory

memory_dir = os.path.expanduser("~/.shrri/memory")
m = Memory()

# Read last 7 days of notes
week_content = []
for i in range(7):
    day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
    fpath = os.path.join(memory_dir, f"{day}.md")
    if os.path.exists(fpath):
        with open(fpath) as f:
            week_content.append(f.read().strip())

if not week_content:
    print("[consolidator] No notes found this week")
    sys.exit(0)

combined = "\n\n".join(week_content)

# Write weekly summary
week_num = datetime.now().strftime("%Y-W%U")
weekly_dir = os.path.expanduser("~/.shrri/memory/weekly")
os.makedirs(weekly_dir, exist_ok=True)
summary_path = os.path.join(weekly_dir, f"{week_num}.md")

with open(summary_path, "w") as f:
    f.write(f"# Weekly Summary — {week_num}\n\n")
    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
    f.write("## This week's conversations\n\n")
    f.write(combined[:3000])

print(f"[consolidator] Weekly summary written to {summary_path}")

# Archive daily notes older than 7 days
archive_dir = os.path.expanduser("~/.shrri/memory/archive")
os.makedirs(archive_dir, exist_ok=True)
cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
archived = 0
for fname in os.listdir(memory_dir):
    if not fname.endswith(".md"):
        continue
    date = fname.replace(".md", "")
    if date < cutoff:
        src = os.path.join(memory_dir, fname)
        dst = os.path.join(archive_dir, fname)
        os.rename(src, dst)
        archived += 1

print(f"[consolidator] Archived {archived} old note files")
