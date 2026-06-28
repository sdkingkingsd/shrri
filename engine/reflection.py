import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.expanduser("~/.shrri/memory.db")


class ReflectionEngine:
    def __init__(self, conn):
        self.conn = conn
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS reflections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                situation TEXT,
                what_went_wrong TEXT,
                correction TEXT,
                learned TEXT,
                timestamp TEXT
            );

            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_phrase TEXT,
                actual_intent TEXT,
                tool TEXT,
                action TEXT,
                success_count INTEGER DEFAULT 1,
                timestamp TEXT
            );

            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT UNIQUE,
                description TEXT,
                example_input TEXT,
                example_output TEXT,
                use_count INTEGER DEFAULT 1,
                timestamp TEXT
            );
        """)
        self.conn.commit()

    def store_correction(self, situation: str, wrong: str, correction: str):
        """Store when user corrects SHRRI."""
        learned = f"When '{situation}', do '{correction}' not '{wrong}'"
        self.conn.execute("""
            INSERT INTO reflections (situation, what_went_wrong, correction, learned, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (situation, wrong, correction, learned, datetime.now().isoformat()))
        self.conn.commit()
        return learned

    def store_pattern(self, user_phrase: str, intent: str, tool: str, action: str):
        """Store a phrase → intent mapping learned from user."""
        existing = self.conn.execute(
            "SELECT id, success_count FROM patterns WHERE user_phrase=? AND tool=?",
            (user_phrase.lower(), tool)
        ).fetchone()

        if existing:
            self.conn.execute(
                "UPDATE patterns SET success_count=? WHERE id=?",
                (existing[1] + 1, existing[0])
            )
        else:
            self.conn.execute("""
                INSERT INTO patterns (user_phrase, actual_intent, tool, action, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (user_phrase.lower(), intent, tool, action, datetime.now().isoformat()))
        self.conn.commit()

    def store_skill(self, name: str, description: str, example_in: str, example_out: str):
        """Store a skill that worked well."""
        existing = self.conn.execute(
            "SELECT id, use_count FROM skills WHERE skill_name=?", (name,)
        ).fetchone()

        if existing:
            self.conn.execute(
                "UPDATE skills SET use_count=? WHERE id=?",
                (existing[1] + 1, existing[0])
            )
        else:
            self.conn.execute("""
                INSERT INTO skills (skill_name, description, example_input, example_output, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (name, description, example_in, example_out, datetime.now().isoformat()))
        self.conn.commit()

    def get_relevant_lessons(self, message: str) -> str:
        """Pull lessons that are actually relevant to the current message.

        Old behavior dumped the top-10 most-used patterns/reflections
        regardless of topic — meaning unrelated noise (e.g. 'hi', or old
        Gmail test queries) got injected into every single prompt, including
        ones about completely unrelated topics, and competed with real live
        data for the model's limited attention. This caused real factual
        hallucinations (e.g. confusing a real internship email with a
        nonexistent 'shopping promotional email').

        Now we only include entries that share real keyword overlap with
        the current message — filtering out common filler/connector words
        first, so something like "explain the mail about the internship"
        can't false-match against an unrelated stored phrase just because
        both happen to contain the word "about".
        """
        # Common connector/filler words that happen to be longer than 3 chars
        # but carry no real topical meaning on their own.
        STOPWORDS = {
            "about", "this", "that", "what", "when", "where", "which",
            "with", "from", "your", "their", "there", "they", "them",
            "have", "does", "doing", "tell", "show", "give", "want",
            "just", "like", "would", "could", "should", "please",
            "explain", "details", "detail",
        }

        def extract_words(text):
            return set(
                w.lower() for w in (text or "").split()
                if len(w) > 3 and w.lower() not in STOPWORDS
            )

        msg_words = extract_words(message)
        if not msg_words:
            return ""

        rows = self.conn.execute(
            "SELECT situation, learned FROM reflections ORDER BY id DESC LIMIT 30"
        ).fetchall()
        patterns = self.conn.execute(
            "SELECT user_phrase, tool, action, success_count FROM patterns ORDER BY success_count DESC LIMIT 30"
        ).fetchall()

        relevant_lessons = []
        for situation, learned in rows:
            sit_words = extract_words(situation)
            if msg_words & sit_words:
                relevant_lessons.append(learned)

        relevant_patterns = []
        for phrase, tool, action, count in patterns:
            phrase_words = extract_words(phrase)
            if msg_words & phrase_words:
                relevant_patterns.append((phrase, tool, action, count))

        output = ""
        if relevant_lessons:
            output += "📚 Relevant past lessons (only shown because they match this topic):\n"
            for l in relevant_lessons[:3]:
                output += f"  - {l}\n"
        if relevant_patterns:
            output += "\n🧠 Relevant past patterns (only shown because they match this topic):\n"
            for phrase, tool, action, count in relevant_patterns[:3]:
                output += f"  - '{phrase}' → {tool}/{action} (used {count}x)\n"

        return output

    def get_all_lessons(self) -> str:
        """Show everything SHRRI has learned."""
        reflections = self.conn.execute(
            "SELECT situation, learned, timestamp FROM reflections ORDER BY id DESC"
        ).fetchall()

        patterns = self.conn.execute(
            "SELECT user_phrase, tool, action, success_count FROM patterns ORDER BY success_count DESC"
        ).fetchall()

        skills = self.conn.execute(
            "SELECT skill_name, description, use_count FROM skills ORDER BY use_count DESC"
        ).fetchall()

        out = "\n==== SHRRI LEARNED SO FAR ====\n"

        out += f"\n📝 Corrections ({len(reflections)}):\n"
        for r in reflections:
            out += f"  [{r[2][:10]}] {r[1]}\n"

        out += f"\n🧠 Patterns ({len(patterns)}):\n"
        for p in patterns:
            out += f"  '{p[0]}' → {p[1]}/{p[2]} ({p[3]}x)\n"

        out += f"\n⚡ Skills ({len(skills)}):\n"
        for s in skills:
            out += f"  {s[0]}: {s[1]} ({s[2]}x)\n"

        return out

    def reflect_on_response(self, router, message: str, response: str) -> str:
        """Full Reflexion loop — Generator → Reflector (loop) → Curator → final answer."""
        import json, re

        # Skip short/casual replies and tool outputs
        if len(response) < 80:
            return response
        tool_signals = ["📧", "🌤", "📩", "✅", "❌", "⚡", "📅", "🔔"]
        if any(s in response for s in tool_signals):
            return response
        meta_signals = ["shrri should", "the response should", "this response", "instead of", "do not"]

        def check_quality(resp):
            prompt = (
                "You are a strict quality checker for SHRRI, a personal AI assistant.\n"
                f"User asked: {message}\n"
                f"SHRRI replied: {resp}\n\n"
                "Check ONLY for these critical problems:\n"
                "1. Hallucination — invented facts, fake names, fake emails, fake dates\n"
                "2. Wrong language — user wrote English but reply is Tamil/Italian/other\n"
                "3. Completely irrelevant — reply has nothing to do with the question\n\n"
                "If no problems: {\"quality\": \"good\"}\n"
                "If problems: {\"quality\": \"bad\", \"reason\": \"brief reason\", \"fixed\": \"corrected reply\"}\n"
                "JSON only, no other text."
            )
            try:
                raw = router.chat(prompt, task="fast", web_search=False)
                raw = re.sub(r"```json|```", "", raw).strip()
                data = json.loads(raw)
                if data.get("quality") == "bad" and data.get("fixed"):
                    fixed = data["fixed"].strip()
                    if any(s in fixed.lower() for s in meta_signals):
                        return True, None
                    return False, fixed
                return True, None
            except Exception:
                return True, None

        # Reflector loop — max 3 attempts
        attempts = [response]
        current = response
        for i in range(3):
            is_good, fixed = check_quality(current)
            if is_good:
                break
            if fixed:
                attempts.append(fixed)
                current = fixed
            else:
                break

        # Curator — pick best if multiple attempts
        if len(attempts) == 1:
            best = attempts[0]
        else:
            options = "\n\n".join(f"Option {i+1}:\n{a}" for i, a in enumerate(attempts))
            curator_prompt = (
                f"You are the Curator for SHRRI. Pick the BEST response to the user.\n"
                f"User asked: {message}\n\n"
                f"{options}\n\n"
                "Respond with ONLY the text of the best option — no labels, no explanation."
            )
            try:
                best = router.chat(curator_prompt, task="fast", web_search=False)
                if not best or len(best) < 10:
                    best = attempts[-1]
            except Exception:
                best = attempts[-1]

        # Save lesson if improved
        if best != response:
            self.store_correction(
                situation=message[:100],
                wrong=response[:100],
                correction=best[:100]
            )

        return best
