import json
import re

CLASSIFY_PROMPT = """Classify this user message into exactly one category based on what kind of help is needed.

Categories:
- "code" — writing, debugging, explaining, or reviewing code/programming
- "plan" — breaking down a goal/project into steps, planning how to approach something
- "research" — looking up facts, asking "what is X", comparisons, asking for information/explanations
- "chat" — casual conversation, greetings, opinions, anything that doesn't clearly fit the above

Respond ONLY with valid JSON, no other text. Format:
{"category": "chat"}

Message: "{message}"
"""

AGENT_PROMPTS = {
    "chat": "",  # uses base SHRRI_SYSTEM as-is, no extra instructions

    "code": """
You are currently acting as SHRRI's coding specialist mode.
Focus on correctness, clear explanations, and working code.
When writing code, use proper formatting and explain key decisions briefly.
If debugging, ask for error messages/tracebacks if not provided.""",

    "plan": """
You are currently acting as SHRRI's planning specialist mode.
Break the user's goal into clear, numbered, actionable steps.
Keep steps concrete and practical, not vague. Mention dependencies between steps if relevant.""",

    "research": """
You are currently acting as SHRRI's research specialist mode.
Be thorough and precise. Explain your reasoning.
If you're uncertain about something, say so rather than guessing confidently.
IMPORTANT: For simple factual questions (capitals, dates, definitions, single facts),
respond in ONE sentence only. Do NOT use numbered steps or headers for simple facts.""",
}

AGENT_TASK_ROUTING = {
    "chat": "default",
    "code": "code",
    "plan": "reason",
    "research": "long",
}


class AgentRouter:
    def __init__(self, router):
        self.router = router

    def classify(self, message):
        """Returns one of: chat, code, plan, research"""
        prompt = CLASSIFY_PROMPT.replace("{message}", message)
        try:
            raw = self.router.chat(prompt, task="fast", web_search=False)
            raw = raw.strip()
            raw = re.sub(r"^```json|```$", "", raw, flags=re.MULTILINE).strip()
            data = json.loads(raw)
            category = data.get("category", "chat")
            if category not in AGENT_PROMPTS:
                return "chat"
            return category
        except Exception:
            return "chat"

    def get_agent_prompt(self, category):
        return AGENT_PROMPTS.get(category, "")

    def get_agent_task(self, category):
        return AGENT_TASK_ROUTING.get(category, "default")
