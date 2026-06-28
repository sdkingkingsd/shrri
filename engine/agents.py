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


import threading

ALWAYS_CHAT = ["i am ", "my name is", "i'm ", "naan ", "என்னோட", "help me", "plan my", "i have", "suggest"]

# Phrases that are always chat, never tool calls
ALWAYS_CHAT = ["i am ", "my name is", "i'm ", "naan ", "என்னோட", "help me", "plan my", "i have", "suggest"]

TASK_SPLIT_PROMPT = """You are a task planner for SHRRI, a personal AI assistant.
Analyze this message and decide if it contains MULTIPLE independent tasks that can run in parallel.

Message: "{message}"

If there are 2 or more independent tasks (e.g. "check my email AND tell me the weather"), respond with JSON:
{{"split": true, "tasks": ["check my email", "tell me the weather"]}}

If it is a single task or a conversation, respond with:
{{"split": false}}

Respond ONLY with valid JSON. No explanation."""


class SubagentExecutor:
    def __init__(self, router, dispatcher_fn, tool_runner_fn):
        self.router = router
        self.dispatch = dispatcher_fn
        self.run_tool = tool_runner_fn

    def should_split(self, message: str) -> list:
        """Ask LLM if message has multiple parallel tasks. Returns list of tasks or []."""
        prompt = TASK_SPLIT_PROMPT.replace("{message}", message)
        try:
            raw = self.router.chat(prompt, task="fast", web_search=False)
            raw = raw.strip().strip("```json").strip("```").strip()
            data = json.loads(raw)
            if data.get("split") and len(data.get("tasks", [])) >= 2:
                return data["tasks"]
        except Exception:
            pass
        return []

    def run_parallel(self, tasks: list) -> str:
        """Run multiple tasks in parallel threads and combine results."""
        results = [None] * len(tasks)
        errors = [None] * len(tasks)

        def run_task(i, task):
            try:
                intent = self.dispatch(task)
                if isinstance(intent, dict) and intent.get("tool") not in ("none", None):
                    tool_result = self.run_tool(intent, task)
                    results[i] = f"[{task}]:\n{tool_result}"
                else:
                    # Pure chat task — ask LLM
                    results[i] = f"[{task}]:\n{self.router.chat(task, task='fast')}"
            except Exception as e:
                errors[i] = f"[{task}]: Error — {e}"

        threads = []
        for i, task in enumerate(tasks):
            t = threading.Thread(target=run_task, args=(i, task))
            t.start()
            threads.append(t)

        for t in threads:
            t.join(timeout=45)

        parts = []
        for i, task in enumerate(tasks):
            if results[i]:
                parts.append(results[i])
            elif errors[i]:
                parts.append(errors[i])
            else:
                parts.append(f"[{task}]: timed out")

        return "\n\n".join(parts)
