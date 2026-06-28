import json
import re

EXTRACT_PROMPT = """Extract personal facts about the user from this message.
Facts include: name, location, college, job, course, year, preferences, likes, dislikes, skills, goals, relationships, habits, devices, language, timezone, possessions.

Rules:
- Extract facts about the USER (Shrridharshan), not about the world
- Key must be a short snake_case identifier (e.g. college, preferred_language, home_city)
- Value must be the exact fact, concise
- Do NOT extract tool results, weather data, or general knowledge as facts

Respond ONLY with valid JSON, no other text. Format:
{"facts": [{"key": "short_key_name", "value": "the fact value"}]}

If no facts are present, respond with:
{"facts": []}

Message: "{message}"
"""

PROACTIVE_SAVE_PROMPT = """You are SHRRI's memory writer. Read this exchange and decide if anything is worth remembering long-term about the user.

User said: "{user_msg}"
SHRRI replied: "{assistant_msg}"

Extract durable facts about the user: preferences, decisions, goals, habits, confirmed settings, things the user wants SHRRI to always remember.

Do NOT save: temporary states, tool outputs, weather, emails, general knowledge.

Respond ONLY with valid JSON:
{"facts": [{"key": "snake_case_key", "value": "fact value"}]}

If nothing worth saving: {"facts": []}
"""

class FactExtractor:
    def __init__(self, router):
        self.router = router

    def extract(self, message):
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
            return []
