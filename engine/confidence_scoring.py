"""
Confidence Scoring — SHRRI Phase 10
Estimates how confident SHRRI is in a response.
"""
import re


def score_confidence(response: str, query: str) -> dict:
    """
    Returns: {"confidence": 0.0-1.0, "level": "high/medium/low", "reason": str}
    """
    # Rule-based fast path
    low_signals = [
        "i'm not sure", "i don't know", "unclear", "uncertain",
        "might be", "could be", "possibly", "gap:", "error",
        "failed", "couldn't", "cannot", "not available"
    ]
    high_signals = [
        "✅", "confirmed", "successfully", "completed",
        "found", "retrieved", "saved"
    ]

    resp_lower = response.lower()
    low_count = sum(1 for s in low_signals if s in resp_lower)
    high_count = sum(1 for s in high_signals if s in resp_lower)

    if low_count >= 2 or response.startswith("GAP"):
        return {"confidence": 0.3, "level": "low", "reason": "uncertainty signals detected"}
    if high_count >= 1 and low_count == 0:
        return {"confidence": 0.9, "level": "high", "reason": "success signals detected"}

    # LLM scoring for ambiguous cases
    try:
        from engine.router import Router
        import json
        r = Router()
        prompt = (
            f"Query: \"{query[:100]}\"\nResponse: \"{response[:200]}\"\n\n"
            "How confident is this response? Reply ONLY as JSON: "
            "{\"confidence\": 0.8, \"reason\": \"one sentence\"}"
        )
        raw = r.chat(prompt, task="fast", web_search=False)
        clean = re.sub(r"```json|```", "", raw).strip()
        data = json.loads(clean)
        conf = float(data.get("confidence", 0.7))
        level = "high" if conf >= 0.8 else "medium" if conf >= 0.5 else "low"
        return {"confidence": conf, "level": level, "reason": data.get("reason", "")}
    except Exception:
        return {"confidence": 0.7, "level": "medium", "reason": "could not score"}


def format_confidence(score: dict) -> str:
    level = score.get("level", "?")
    conf = int(score.get("confidence", 0) * 100)
    reason = score.get("reason", "")
    emoji = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(level, "⚪")
    return f"{emoji} Confidence: {level} ({conf}%) — {reason}"
