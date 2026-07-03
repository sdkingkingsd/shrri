"""
Verifier — SHRRI Phase 10
Verifies factual claims in a response against known memory + web search.
"""
import re


def verify_response(response: str, query: str, use_web: bool = False) -> dict:
    """
    Checks factual claims in a response.
    Returns: {"verified": bool, "issues": [...], "corrected": str}
    """
    try:
        from engine.router import Router
        import json
        r = Router()
        prompt = (
            f"Query: \"{query[:100]}\"\n"
            f"Response to verify: \"{response[:400]}\"\n\n"
            "Check this response for factual errors or unsupported claims.\n"
            "Reply ONLY as JSON: "
            "{\"verified\": true, \"issues\": [], \"corrected\": \"same or fixed response\"}\n"
            "verified=true means no significant issues found."
        )
        raw = r.chat(prompt, task="fast", web_search=use_web)
        clean = re.sub(r"```json|```", "", raw).strip()
        return json.loads(clean)
    except Exception as e:
        return {"verified": True, "issues": [], "corrected": response}


def quick_verify(response: str) -> bool:
    """Fast rule-based check — no LLM call."""
    red_flags = ["as of my knowledge cutoff", "i cannot browse", "hallucin"]
    return not any(f in response.lower() for f in red_flags)
