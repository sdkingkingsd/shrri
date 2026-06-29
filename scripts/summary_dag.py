#!/usr/bin/env python3
"""
SHRRI Summary DAG
Lightweight implementation inspired by hermes-lcm
D0 = raw messages, D1 = hourly summaries, D2 = daily summaries
"""
import sys, os, sqlite3, json
from datetime import datetime, timedelta
sys.path.insert(0, '/home/shrridharshan/shrri')

DB_PATH = "/home/shrridharshan/.shrri/conversations.db"

def get_conn():
    return sqlite3.connect(DB_PATH)

def setup_dag_tables():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS summary_dag (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level INTEGER,          -- 0=raw, 1=hourly, 2=daily
            parent_id INTEGER,      -- parent summary node
            session_date TEXT,      -- YYYY-MM-DD
            session_hour TEXT,      -- YYYY-MM-DD-HH
            summary TEXT,           -- compressed summary text
            message_ids TEXT,       -- JSON list of conversation row ids
            created_at TEXT,
            FOREIGN KEY(parent_id) REFERENCES summary_dag(id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_dag_level ON summary_dag(level)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_dag_date ON summary_dag(session_date)
    """)
    conn.commit()
    conn.close()
    print("[dag] Tables ready")

def build_hourly_summaries(date=None):
    """D0 -> D1: Group raw messages by hour, create summary nodes"""
    conn = get_conn()
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    # Get all messages for this date grouped by hour
    rows = conn.execute("""
        SELECT id, role, message, timestamp
        FROM conversations
        WHERE date(timestamp) = ?
        ORDER BY timestamp ASC
    """, (date,)).fetchall()

    if not rows:
        print(f"[dag] No messages for {date}")
        conn.close()
        return

    # Group by hour
    hours = {}
    for row in rows:
        ts = row[3][:13]  # YYYY-MM-DDTHH
        if ts not in hours:
            hours[ts] = []
        hours[ts].append(row)

    created = 0
    for hour, msgs in hours.items():
        # Check if summary already exists for this hour
        existing = conn.execute(
            "SELECT id FROM summary_dag WHERE level=1 AND session_hour=?", (hour,)
        ).fetchone()
        if existing:
            continue

        # Build summary text
        user_msgs = [m[2][:100] for m in msgs if m[1] == "user"]
        summary = f"Hour {hour}: {len(msgs)} messages. Topics: " + "; ".join(user_msgs[:5])

        msg_ids = json.dumps([m[0] for m in msgs])
        conn.execute("""
            INSERT INTO summary_dag (level, session_date, session_hour, summary, message_ids, created_at)
            VALUES (1, ?, ?, ?, ?, ?)
        """, (date, hour, summary[:500], msg_ids, datetime.now().isoformat()))
        created += 1

    conn.commit()
    conn.close()
    print(f"[dag] Created {created} hourly summary nodes for {date}")

def build_daily_summary(date=None):
    """D1 -> D2: Combine hourly summaries into daily summary"""
    conn = get_conn()
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    # Check if daily summary already exists
    existing = conn.execute(
        "SELECT id FROM summary_dag WHERE level=2 AND session_date=?", (date,)
    ).fetchone()
    if existing:
        print(f"[dag] Daily summary for {date} already exists")
        conn.close()
        return

    # Get all hourly summaries for this date
    hourly = conn.execute("""
        SELECT id, summary FROM summary_dag
        WHERE level=1 AND session_date=?
        ORDER BY session_hour ASC
    """, (date,)).fetchall()

    if not hourly:
        print(f"[dag] No hourly summaries for {date}")
        conn.close()
        return

    # Combine into daily summary
    daily_text = f"Daily summary for {date}:\n"
    parent_ids = []
    for h in hourly:
        daily_text += f"- {h[1]}\n"
        parent_ids.append(h[0])

    conn.execute("""
        INSERT INTO summary_dag (level, session_date, summary, message_ids, created_at)
        VALUES (2, ?, ?, ?, ?)
    """, (date, daily_text[:1000], json.dumps(parent_ids), datetime.now().isoformat()))
    conn.commit()
    conn.close()
    print(f"[dag] Created daily summary for {date}")

def expand_summary(date):
    """Expand a daily summary back to hourly details"""
    conn = get_conn()
    daily = conn.execute("""
        SELECT id, summary FROM summary_dag
        WHERE level=2 AND session_date=?
    """, (date,)).fetchone()

    if not daily:
        print(f"[dag] No daily summary for {date}")
        conn.close()
        return None

    hourly = conn.execute("""
        SELECT session_hour, summary FROM summary_dag
        WHERE level=1 AND session_date=?
        ORDER BY session_hour ASC
    """, (date,)).fetchall()

    conn.close()
    result = f"=== {date} ===\n{daily[1]}\n\n=== Hourly Breakdown ===\n"
    for h in hourly:
        result += f"\n{h[0]}:\n{h[1]}\n"
    return result

def search_dag(query):
    """Search across all summary nodes"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT level, session_date, session_hour, summary
        FROM summary_dag
        WHERE summary LIKE ?
        ORDER BY session_date DESC, level DESC
        LIMIT 5
    """, (f"%{query}%",)).fetchall()
    conn.close()
    return rows

if __name__ == "__main__":
    setup_dag_tables()
    build_hourly_summaries()
    build_daily_summary()
    print("[dag] Done")
    # Show what we built
    conn = get_conn()
    nodes = conn.execute("SELECT level, session_date, session_hour, substr(summary,1,80) FROM summary_dag").fetchall()
    for n in nodes:
        print(f"  L{n[0]} | {n[1]} | {n[2]} | {n[3]}")
    conn.close()
