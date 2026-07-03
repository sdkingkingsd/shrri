"""
Self Critic — SHRRI Phase 10
Reviews its own output before sending, flags issues, suggests improvements.
"""


def critique(response: str, original_query: str) -> dict:
    """
    Critique a response before sending.
    Returns: {"score": 0-10, "issues": [...], "improved": str}
    """
    try:
        from engine.router import Router
        import json, re
        r = Router()
        prompt = (
            f"Original query: \"{original_query}\"\n"
            f"Response to critique: \"{response[:500]}\"\n\n"
            "Critique this response. Reply ONLY as JSON:\n"
            "{\"score\": 8, \"issues\": [\"issue1\"], \"improved\": \"better version\"}\n"
            "score = 0-10 (10=perfect). issues = list of problems (empty if none). "
            "improved = rewritten response if score < 7, else same as original."
        )
        raw = r.chat(prompt, task="fast", web_search=False)
        clean = re.sub(r"```json|```", "", raw).strip()
        return json.loads(clean)
    except Exception as e:
        return {"score": 7, "issues": [], "improved": response}


def should_critique(response: str, query: str) -> bool:
    """Only critique responses that are substantial enough to matter."""
    if len(response) < 50:
        return False
    if response.startswith("GAP:") or response.startswith("✅"):
        return False
    return True
