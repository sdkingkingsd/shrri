"""
Hybrid Routing — SHRRI AI OS v2

Splits a single request across local + cloud: a fast, free local
model triages the prompt first ("can you answer this well yourself?"),
and only escalates to the full cloud candidate list (route()) when
local says it can't handle it well, or fails outright.

This is additive on top of everything else in Phase 3 — Model
Selection still picks the capability, Provider Ranking + Offline
First still govern ordering *within* the cloud escalation path.
Hybrid Routing only decides whether to escalate at all.
"""

from engine.provider_registry import registry
from engine.multi_router import route as _route

_TRIAGE_MODEL = "qwen2.5:3b"

_TRIAGE_SYSTEM_PROMPT = (
    "You are a fast triage assistant. You will be shown a user prompt. "
    "Decide if a small local model (you) can answer it well, or if it "
    "needs a larger, more capable model. Reply with EXACTLY one word: "
    "LOCAL if you can answer it well yourself, or ESCALATE if it needs "
    "a bigger model (e.g. complex reasoning, coding, long-form writing, "
    "specialized knowledge, or anything you're unsure about). "
    "Reply with only that one word, nothing else."
)


def _triage(prompt: str, verbose: bool = False) -> str:
    """
    Ask the local model to self-assess. Returns 'LOCAL' or 'ESCALATE'.
    Any failure (Ollama down, bad response, etc.) defaults to
    'ESCALATE' — fail safe towards the more capable path rather than
    silently returning a weak local answer.
    """
    try:
        provider = registry.get_instance("local", "local")
        response = provider.chat(prompt, _TRIAGE_MODEL, system=_TRIAGE_SYSTEM_PROMPT)
        verdict = response.strip().upper()
        if verbose:
            print(f"[hybrid_router] Triage verdict: {verdict!r}")
        if "ESCALATE" in verdict:
            return "ESCALATE"
        if "LOCAL" in verdict:
            return "LOCAL"
        # Unexpected response — fail safe to escalate
        if verbose:
            print(f"[hybrid_router] Unexpected triage response, escalating to be safe.")
        return "ESCALATE"
    except Exception as e:
        if verbose:
            print(f"[hybrid_router] Triage failed ({e}), escalating to be safe.")
        return "ESCALATE"


def route_hybrid(capability: str, prompt: str, verbose: bool = False) -> dict:
    """
    Hybrid-routed version of route(). Triages locally first; only
    calls the full route() (cloud candidate list) if triage says
    ESCALATE or triage itself fails.
    """
    verdict = _triage(prompt, verbose=verbose)

    if verdict == "LOCAL":
        try:
            provider = registry.get_instance("local", "local")
            response = provider.chat(prompt, _TRIAGE_MODEL)
            return {
                "provider": "local",
                "model": _TRIAGE_MODEL,
                "response": response,
                "success": True,
                "hybrid_path": "local_only",
            }
        except Exception as e:
            if verbose:
                print(f"[hybrid_router] Local answer failed after LOCAL verdict, escalating: {e}")
            # fall through to escalation below

    result = _route(capability, prompt, verbose=verbose)
    result["hybrid_path"] = "escalated"
    return result
