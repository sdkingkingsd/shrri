import json
import re

EXTRACT_PROMPT = """Extract any personal facts the user stated about themselves from this message. 
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
            return []
