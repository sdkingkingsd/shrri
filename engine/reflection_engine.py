"""
Reflection Engine — SHRRI Phase 10
After completing a task, reflects on what happened, what could be better,
and stores the lesson in episodic memory.
"""
from datetime import datetime


def reflect(task: str, result: str, success: bool, session_id: str = "") -> str:
    """
    Reflect on a completed task and store the lesson.
    Returns the reflection text.
    """
    try:
        from engine.router import Router
        from engine.episodic_memory import EpisodicMemory

        r = Router()
        prompt = (
            f"You just completed this task: \"{task}\"\n"
            f"Result: \"{result[:300]}\"\n"
            f"Success: {success}\n\n"
            "In 2-3 sentences, reflect on:\n"
            "1. What worked or didn't work\n"
            "2. What you'd do differently next time\n"
            "Keep it concise and actionable."
        )
        reflection = r.chat(prompt, task="fast", web_search=False)

        em = EpisodicMemory()
        em.record_episode(
            event_type="reflection",
            summary=f"Reflected on: {task[:60]}",
            context=reflection,
            outcome="success" if success else "failure",
            importance=6 if success else 7,
            session_id=session_id
        )
        em.record_experience(
            skill=task[:40],
            what_worked=result[:100] if success else "",
            what_failed="" if success else result[:100],
            lesson=reflection[:200]
        )
        return reflection
    except Exception as e:
        return f"Reflection error: {e}"


def reflect_on_conversation(turns: list, session_id: str = "") -> str:
    """Reflect on an entire conversation session."""
    try:
        from engine.router import Router
        r = Router()
        summary = "\n".join(f"{t['role']}: {t['content'][:100]}" for t in turns[-6:])
        prompt = (
            f"Review this conversation:\n{summary}\n\n"
            "In 2 sentences: what was accomplished and what could be improved?"
        )
        return r.chat(prompt, task="fast", web_search=False)
    except Exception as e:
        return f"Reflection error: {e}"
