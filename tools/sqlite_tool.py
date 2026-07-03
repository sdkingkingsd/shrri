"""SQLite tool — query and manage local SQLite databases."""
import sqlite3, os, re

def sqlite_query(prompt: str) -> str:
    """Parse prompt for db path + SQL and execute it."""
    try:
        # Extract db path
        m = re.search(r'([~\w/.]+\.(?:db|sqlite|sqlite3))', prompt, re.I)
        if m:
            db_path = os.path.expanduser(m.group(1).strip())
        else:
            db_path = os.path.expanduser("~/.shrri/shrri.db")

        # Extract SQL
        # Strip db path reference before extracting SQL
        clean_prompt = re.sub(r'\s+db\s+\S+\.(?:db|sqlite|sqlite3)', '', prompt, flags=re.I)
        sql_m = re.search(r'(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|PRAGMA).+', clean_prompt, re.I | re.DOTALL)
        if not sql_m:
            # List tables if no SQL given
            conn = sqlite3.connect(db_path)
            cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [r[0] for r in cur.fetchall()]
            conn.close()
            if not tables:
                return f"Database {db_path} has no tables."
            return f"Tables in {db_path}:\n" + "\n".join(f"  - {t}" for t in tables)

        sql = sql_m.group(0).strip()
        conn = sqlite3.connect(db_path)
        cur = conn.execute(sql)
        if sql.strip().upper().startswith("SELECT") or sql.strip().upper().startswith("PRAGMA"):
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
            conn.close()
            if not rows:
                return "Query returned no results."
            lines = [" | ".join(cols)]
            lines.append("-" * len(lines[0]))
            for row in rows[:20]:
                lines.append(" | ".join(str(v) for v in row))
            if len(rows) > 20:
                lines.append(f"... and {len(rows)-20} more rows")
            return "\n".join(lines)
        else:
            conn.commit()
            affected = cur.rowcount
            conn.close()
            return f"✅ Query executed. Rows affected: {affected}"
    except Exception as e:
        return f"GAP: SQLite error — {e}"
