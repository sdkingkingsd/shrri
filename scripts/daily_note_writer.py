#!/usr/bin/env python3
"""
SHRRI Daily Note Writer
Reads today's conversations from DB and writes a summary to ~/.shrri/memory/YYYY-MM-DD.md
"""
import sys, os
from datetime import datetime
sys.path.insert(0, '/home/shrridharshan/shrri')
from engine.memory import Memory

m = Memory()
today = datetime.now().strftime("%Y-%m-%d")
note_path = os.path.expanduser(f"~/.shrri/memory/{today}.md")

# Get today's conversations
rows = m.conn.execute("""
    SELECT role, content, timestamp FROM conversations
    WHERE date(timestamp) = date('now', 'localtime')
    ORDER BY timestamp ASC
""").fetchall()

if not rows:
    print("[daily_note] No conversations today, skipping")
    sys.exit(0)

# Build summary
lines = [f"# SHRRI Daily Notes — {today}\n"]
lines.append(f"Total messages: {len(rows)}\n")
lines.append("## Conversation Summary\n")

# Extract key points — user messages only
user_msgs = [r[1] for r in rows if r[0] == "user"]
assistant_msgs = [r[1] for r in rows if r[0] == "assistant"]

lines.append(f"- Topics discussed: {len(user_msgs)} exchanges\n")

# Write last 10 user messages as context
lines.append("\n## What Shrri asked today\n")
for msg in user_msgs[-10:]:
    clean = msg.strip()[:120].replace("\n", " ")
    lines.append(f"- {clean}\n")

# Write to file (append if exists)
mode = "a" if os.path.exists(note_path) else "w"
with open(note_path, mode) as f:
    if mode == "a":
        f.write(f"\n---\n## Update at {datetime.now().strftime('%H:%M')}\n")
    f.writelines(lines)

print(f"[daily_note] Written to {note_path}")
