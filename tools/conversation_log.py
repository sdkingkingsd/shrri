import sqlite3, os, datetime

DB_PATH = os.path.expanduser("~/.shrri/conversations.db")

def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            role TEXT,
            message TEXT
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts
        USING fts5(message, content=conversations, content_rowid=id);
        CREATE TRIGGER IF NOT EXISTS conv_ai AFTER INSERT ON conversations BEGIN
            INSERT INTO conversations_fts(rowid, message) VALUES (new.id, new.message);
        END;
    """)
    conn.commit()
    return conn

def log_turn(user_msg: str, shrri_msg: str):
    """Save a conversation turn to the log."""
    conn = _get_conn()
    ts = datetime.datetime.now().isoformat()
    conn.execute("INSERT INTO conversations (timestamp, role, message) VALUES (?, ?, ?)",
                 (ts, "user", user_msg))
    conn.execute("INSERT INTO conversations (timestamp, role, message) VALUES (?, ?, ?)",
                 (ts, "shrri", shrri_msg))
    conn.commit()
    conn.close()

def search_conversations(query: str, limit: int = 5) -> str:
    """Search past conversations using full-text search."""
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT c.timestamp, c.role, c.message
            FROM conversations c
            JOIN conversations_fts fts ON c.id = fts.rowid
            WHERE conversations_fts MATCH ?
            ORDER BY c.timestamp DESC
            LIMIT ?
        """, (query, limit * 2)).fetchall()
    except Exception as e:
        return f"Search error: {e}"
    finally:
        conn.close()

    if not rows:
        return f"No past conversations found about '{query}'."

    lines = [f"Past conversations about '{query}':\n"]
    seen = set()
    for ts, role, msg in rows:
        date = ts[:10]
        preview = msg[:120].replace("\n", " ")
        key = preview[:40]
        if key not in seen:
            seen.add(key)
            who = "You" if role == "user" else "SHRRI"
            lines.append(f"  [{date}] {who}: {preview}")
    return "\n".join(lines[:limit + 1])

def get_recent(days: int = 1) -> str:
    """Get recent conversations."""
    conn = _get_conn()
    since = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
    rows = conn.execute("""
        SELECT timestamp, role, message FROM conversations
        WHERE timestamp > ?
        ORDER BY timestamp DESC LIMIT 20
    """, (since,)).fetchall()
    conn.close()
    if not rows:
        return f"No conversations in the last {days} day(s)."
    lines = [f"Recent conversations (last {days} day):\n"]
    for ts, role, msg in rows:
        date = ts[11:16]
        who = "You" if role == "user" else "SHRRI"
        lines.append(f"  [{date}] {who}: {msg[:100]}")
    return "\n".join(lines)
