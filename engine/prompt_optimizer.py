"""
Prompt Optimizer — SHRRI Phase 11
Improves prompts based on past failures and reflection history.
"""
import re


def optimize_prompt(prompt: str, task_type: str = "general") -> str:
    """Improve a prompt using learned patterns."""
    try:
        from engine.router import Router
        from engine.memory import Memory

        m = Memory()
        lessons = ""
        facts = m.get_all_facts()
        relevant = {k: v for k, v in facts.items() if any(
            w in prompt.lower() for w in k.lower().split("_")
        )}
        if relevant:
            lessons = "Known context: " + "; ".join(f"{k}={v}" for k, v in list(relevant.items())[:3])

        r = Router()
        meta_prompt = (
            f"Improve this prompt for a {task_type} task. Make it clearer and more specific.\n"
            f"Original: \"{prompt}\"\n"
            f"{lessons}\n"
            "Return ONLY the improved prompt, nothing else."
        )
        improved = r.chat(meta_prompt, task="fast", web_search=False)
        return improved.strip() if improved.strip() else prompt
    except Exception:
        return prompt


def optimize_system_prompt(base_prompt: str) -> str:
    """Enhance the system prompt with AI DNA identity."""
    try:
        from engine.ai_dna import AIDNA
        dna = AIDNA()
        identity = dna.get_identity_prompt()
        return f"{identity}\n\n{base_prompt}"
    except Exception:
        return base_prompt


class PromptOptimizer:
    """Wrapper class for prompt optimization functions."""
    def optimize(self, prompt: str, task_type: str = "general") -> str:
        return optimize_prompt(prompt, task_type)

    def optimize_with_dna(self, prompt: str) -> str:
        return optimize_with_ai_dna(prompt)
