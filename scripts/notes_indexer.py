#!/usr/bin/env python3
"""
SHRRI Notes Indexer
Indexes all daily note files into SQLite FTS5 for cross-session search
"""
import sys, os, sqlite3
from datetime import datetime
sys.path.insert(0, '/home/shrridharshan/shrri')

db_path = os.path.expanduser("~/.shrri/conversations.db")
conn = sqlite3.connect(db_path)

# Create notes FTS table if not exists
conn.execute("""
    CREATE TABLE IF NOT EXISTS daily_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT UNIQUE,
        content TEXT,
        indexed_at TEXT
    )
""")
conn.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS daily_notes_fts
    USING fts5(date, content, content='daily_notes', content_rowid='id')
""")
conn.commit()

# Index all daily note files
memory_dir = os.path.expanduser("~/.shrri/memory")
indexed = 0
for fname in sorted(os.listdir(memory_dir)):
    if not fname.endswith(".md"):
        continue
    date = fname.replace(".md", "")
    fpath = os.path.join(memory_dir, fname)
    with open(fpath) as f:
        content = f.read().strip()
    if not content:
        continue
    # Upsert into daily_notes
    conn.execute("""
        INSERT INTO daily_notes (date, content, indexed_at)
        VALUES (?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET content=excluded.content, indexed_at=excluded.indexed_at
    """, (date, content, datetime.now().isoformat()))
    indexed += 1

# Rebuild FTS index
conn.execute("INSERT INTO daily_notes_fts(daily_notes_fts) VALUES('rebuild')")
conn.commit()
conn.close()
print(f"[notes_indexer] Indexed {indexed} daily note files")
