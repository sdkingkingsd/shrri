#!/bin/bash
# SHRRI Long-term Memory Fix — apply on your laptop
# Run from: /home/shrridharshan/shrri/
set -e

echo "=== SHRRI Memory Fix: Long-term Facts → 100% ==="

cd ~/shrri

# ── Step 1: Backup ──────────────────────────────────────────────
cp engine/memory.py   engine/memory.py.bak_memfix
cp engine/extractor.py engine/extractor.py.bak_memfix
cp engine/client.py   engine/client.py.bak_memfix
echo "✓ Backups done"

# ── Step 2: Patch memory.py ─────────────────────────────────────
python3 << 'PYEOF'
path = "engine/memory.py"
with open(path) as f:
    c = f.read()

# 2a — add updated_at + fact_history table
old = '''            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                created_at TEXT
            );'''
new = '''            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS fact_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT,
                old_value TEXT,
                new_value TEXT,
                changed_at TEXT
            );'''
assert old in c, "ABORT: facts schema anchor not found"
c = c.replace(old, new)

# 2b — save_fact with history tracking
old = '''    def save_fact(self, key, value):
        self.conn.execute("""
            INSERT INTO facts (key, value, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """, (key, value, datetime.now().isoformat()))
        self.conn.commit()
        self._save_encrypted()'''
new = '''    def save_fact(self, key, value):
        now = datetime.now().isoformat()
        existing = self.conn.execute(
            "SELECT value FROM facts WHERE key=?", (key,)
        ).fetchone()
        if existing and existing[0] != value:
            self.conn.execute(
                "INSERT INTO fact_history (key, old_value, new_value, changed_at) VALUES (?, ?, ?, ?)",
                (key, existing[0], value, now)
            )
        self.conn.execute("""
            INSERT INTO facts (key, value, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
        """, (key, value, now, now))
        self.conn.commit()
        self._save_encrypted()'''
assert old in c, "ABORT: save_fact anchor not found"
c = c.replace(old, new)

# 2c — add get_fact_history + delete_fact after get_all_facts
old = '''    def get_all_facts(self):
        rows = self.conn.execute(
            "SELECT key, value FROM facts"
        ).fetchall()
        return {r[0]: r[1] for r in rows}'''
new = '''    def get_all_facts(self):
        rows = self.conn.execute(
            "SELECT key, value FROM facts"
        ).fetchall()
        return {r[0]: r[1] for r in rows}

    def get_fact_history(self, key=None):
        """History of fact changes. Pass key to filter by one fact."""
        if key:
            rows = self.conn.execute(
                "SELECT key, old_value, new_value, changed_at FROM fact_history WHERE key=? ORDER BY changed_at DESC LIMIT 10",
                (key,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT key, old_value, new_value, changed_at FROM fact_history ORDER BY changed_at DESC LIMIT 20"
            ).fetchall()
        return [{"key": r[0], "old": r[1], "new": r[2], "when": r[3]} for r in rows]

    def delete_fact(self, key):
        """Delete a specific fact by key."""
        self.conn.execute("DELETE FROM facts WHERE key=?", (key,))
        self.conn.commit()
        self._save_encrypted()'''
assert old in c, "ABORT: get_all_facts anchor not found"
c = c.replace(old, new)

with open(path, 'w') as f:
    f.write(c)
print("✓ memory.py patched")
PYEOF

# ── Step 3: Patch extractor.py ──────────────────────────────────
python3 << 'PYEOF'
path = "engine/extractor.py"
with open(path) as f:
    c = f.read()

old = '''EXTRACT_PROMPT = """Extract any personal facts the user stated about themselves from this message. 
Facts include: name, location, college, job, preferences, likes, dislikes, skills, goals, relationships, possessions.

Respond ONLY with valid JSON, no other text. Format:
{"facts": [{"key": "short_key_name", "value": "the fact value"}]}

If no facts are stated, respond with:
{"facts": []}

Message: "{message}"
"""

class FactExtractor:
    def __init__(self, router):
        self.router = router

    def extract(self, message):
        prompt = EXTRACT_PROMPT.replace("{message}", message)
        try:
            raw = self.router.chat(prompt, task="fast", web_search=False)
            raw = raw.strip()
            # strip markdown fences if present
            raw = re.sub(r"^```json|```$", "", raw, flags=re.MULTILINE).strip()
            data = json.loads(raw)
            return data.get("facts", [])
        except Exception:
            return []'''

new = '''EXTRACT_PROMPT = """Extract personal facts about the user from this message.
Facts include: name, location, college, job, course, year, preferences, likes, dislikes, skills, goals, relationships, habits, devices, language, timezone, possessions.

Rules:
- Extract facts about the USER (Shrridharshan), not about the world
- Key must be a short snake_case identifier (e.g. college, preferred_language, home_city)
- Value must be the exact fact, concise (e.g. "PSG College of Technology", "Tamil", "Salem")
- If the same fact already seems implied, still return it — the system handles deduplication
- Do NOT extract tool results, weather data, or general knowledge as facts

Respond ONLY with valid JSON, no other text. Format:
{"facts": [{"key": "short_key_name", "value": "the fact value"}]}

If no facts are present, respond with:
{"facts": []}

Message: "{message}"
"""

PROACTIVE_SAVE_PROMPT = """You are SHRRI\'s memory writer. Read this conversation exchange and decide if there is anything important to remember long-term about the user.

User said: "{user_msg}"
SHRRI replied: "{assistant_msg}"

Extract any durable facts about the user revealed in this exchange.
Facts include: preferences, decisions, goals, habits, relationships, settings the user confirmed, things the user wants SHRRI to always do/remember.

Do NOT save:
- temporary states ("user is angry right now")
- tool outputs (weather, emails)
- general knowledge

Respond ONLY with valid JSON:
{"facts": [{"key": "snake_case_key", "value": "fact value"}]}

If nothing worth saving: {"facts": []}
"""

class FactExtractor:
    def __init__(self, router):
        self.router = router

    def extract(self, message):
        """Extract facts from a user message."""
        prompt = EXTRACT_PROMPT.replace("{message}", message)
        try:
            raw = self.router.chat(prompt, task="fast", web_search=False)
            raw = raw.strip()
            raw = re.sub(r"^```json|```$", "", raw, flags=re.MULTILINE).strip()
            data = json.loads(raw)
            return data.get("facts", [])
        except Exception:
            return []

    def extract_from_exchange(self, user_msg: str, assistant_msg: str):
        """Proactive save — SHRRI decides what to remember from the full exchange.
        Catches facts that only become clear from context, e.g. confirmed settings,
        user preferences revealed through how they reacted to a response.
        """
        if len(user_msg.split()) < 3 or len(assistant_msg.split()) < 3:
            return []
        tool_signals = ["📧", "🌤", "📩", "✅", "❌", "📅", "🔔", "⏰", "Current time:"]
        if any(s in assistant_msg for s in tool_signals):
            return []
        try:
            prompt = (PROACTIVE_SAVE_PROMPT
                      .replace("{user_msg}", user_msg[:400])
                      .replace("{assistant_msg}", assistant_msg[:400]))
            raw = self.router.chat(prompt, task="fast", web_search=False)
            raw = raw.strip()
            raw = re.sub(r"^```json|```$", "", raw, flags=re.MULTILINE).strip()
            data = json.loads(raw)
            return data.get("facts", [])
        except Exception:
            return []'''

assert old in c, "ABORT: extractor anchor not found"
c = c.replace(old, new)
with open(path, 'w') as f:
    f.write(c)
print("✓ extractor.py patched")
PYEOF

# ── Step 4: Patch client.py ─────────────────────────────────────
python3 << 'PYEOF'
path = "engine/client.py"
with open(path) as f:
    c = f.read()

# 4a — proactive exchange extraction after auto-extract block
old = '''        # Auto-extract facts
        extract_input_tokens = 0
        should_extract = len(message.split()) >= 5
        if should_extract:
            try:
                extract_prompt_text = EXTRACT_PROMPT.replace("{message}", message)
                extract_input_tokens = count_tokens(extract_prompt_text)
                new_facts = self.extractor.extract(message)
                for f in new_facts:
                    key = f.get("key")
                    value = f.get("value")
                    if key and value:
                        self.memory.save_fact(key, value)
                        pass  # silent learn
            except Exception:
                pass'''

new = '''        # Auto-extract facts from user message
        extract_input_tokens = 0
        should_extract = len(message.split()) >= 5
        if should_extract:
            try:
                extract_prompt_text = EXTRACT_PROMPT.replace("{message}", message)
                extract_input_tokens = count_tokens(extract_prompt_text)
                new_facts = self.extractor.extract(message)
                for f in new_facts:
                    key = f.get("key")
                    value = f.get("value")
                    if key and value:
                        self.memory.save_fact(key, value)
                        pass  # silent learn
            except Exception:
                pass

        # Proactive fact save — SHRRI decides what to remember from the full exchange
        # Runs every 3 turns to avoid burning tokens on every single message
        try:
            msg_count = self.memory.conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
            if should_extract and msg_count % 3 == 0:
                proactive_facts = self.extractor.extract_from_exchange(message, response)
                for f in proactive_facts:
                    key = f.get("key")
                    value = f.get("value")
                    if key and value:
                        self.memory.save_fact(key, value)
                        print(f"[SHRRI] Proactively saved: {key} = {value}")
        except Exception:
            pass'''

assert old in c, "ABORT: extract anchor not found"
c = c.replace(old, new)

# 4b — forget/remember/history commands
old = '''        # Handle "what do you know about me" directly from facts
        know_triggers = ["what do you know about me", "what you know about me",
                         "tell me about myself", "what do you know about shrri",
                         "what you know", "ennai pathi sollu", "about me"]
        if any(message.lower().strip() == t for t in know_triggers):
            facts = self.memory.get_all_facts()
            if facts:
                lines = [f"- {k}: {v}" for k, v in facts.items()]
                return "Here's what I know about you:\\n" + "\\n".join(lines)
            return "I don't have any facts stored about you yet. Tell me something!"'''

new = '''        # Handle "what do you know about me" directly from facts
        know_triggers = ["what do you know about me", "what you know about me",
                         "tell me about myself", "what do you know about shrri",
                         "what you know", "ennai pathi sollu", "about me"]
        if any(message.lower().strip() == t for t in know_triggers):
            facts = self.memory.get_all_facts()
            if facts:
                lines = [f"- {k}: {v}" for k, v in facts.items()]
                return "Here's what I know about you:\\n" + "\\n".join(lines)
            return "I don't have any facts stored about you yet. Tell me something!"

        # "forget X" — delete a specific fact
        msg_stripped = message.lower().strip()
        if msg_stripped.startswith("forget "):
            key_to_forget = message.strip()[7:].strip().lower().replace(" ", "_")
            self.memory.delete_fact(key_to_forget)
            return f"✅ Forgotten: {key_to_forget}"

        # "remember that X" / "always remember X" — force save a fact manually
        if msg_stripped.startswith("remember that ") or msg_stripped.startswith("always remember "):
            fact_text = " ".join(message.strip().split(" ")[2:])
            new_facts = self.extractor.extract(fact_text)
            saved = []
            for f in new_facts:
                key = f.get("key")
                value = f.get("value")
                if key and value:
                    self.memory.save_fact(key, value)
                    saved.append(f"{key}: {value}")
            if saved:
                return "✅ Remembered:\\n" + "\\n".join(f"- {s}" for s in saved)
            self.memory.save_fact("note_" + fact_text[:30].replace(" ", "_"), fact_text)
            return f"✅ Remembered: {fact_text}"

        # "fact history" / "what changed" — show what facts were updated
        if msg_stripped in ("fact history", "what changed", "what did you change", "memory history"):
            history = self.memory.get_fact_history()
            if not history:
                return "No fact changes recorded yet."
            lines = [f"- [{h['when'][:10]}] {h['key']}: \\'{h['old']}\\' → \\'{h['new']}\\'" for h in history]
            return "📋 Recent fact changes:\\n" + "\\n".join(lines)'''

assert old in c, "ABORT: know_triggers anchor not found"
c = c.replace(old, new)

with open(path, 'w') as f:
    f.write(c)
print("✓ client.py patched")
PYEOF

# ── Step 5: Syntax check ────────────────────────────────────────
python3 -c "
import py_compile
py_compile.compile('engine/memory.py', doraise=True)
py_compile.compile('engine/extractor.py', doraise=True)
py_compile.compile('engine/client.py', doraise=True)
print('✓ All 3 files syntax OK')
"

# ── Step 6: Git commit ───────────────────────────────────────────
git add engine/memory.py engine/extractor.py engine/client.py
git commit -m "Long-term facts → 100%: updated_at + fact_history table, proactive exchange extraction, forget/remember/history commands, expanded extractor prompt"

echo ""
echo "=== Done! Now restart SHRRI: ==="
echo "  systemctl --user restart shrri-telegram"
echo ""
echo "Test in Telegram:"
echo "  'remember that I prefer dark mode'"
echo "  'what do you know about me'"
echo "  'forget preferred_language'"
echo "  'fact history'"
