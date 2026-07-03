# config/capability_map.py
"""
Each capability maps to an ORDERED list of (provider, model) candidates.
Router tries them in order until one succeeds.
"""

CAPABILITIES = {

    "conversation": {
        "providers": [
            ("groq", "llama-3.3-70b-versatile"),
            ("cerebras", "gpt-oss-120b"),
            ("google", "gemini-2.5-flash"),
            ("nara", "claude-haiku-4.5"),
            ("local", "qwen2.5:3b"),
        ],
    },

    "reasoning": {
        "providers": [
            ("cerebras", "gpt-oss-120b"),
            ("google", "gemini-2.5-flash"),
            ("local", "qwen2.5:3b"),
        ],
    },

    "coding": {
        "providers": [
            
            ("openrouter", "google/gemma-4-26b-a4b-it:free"),
            ("groq", "llama-3.3-70b-versatile"),
            ("local", "qwen2.5-coder:7b"),
        ],
    },

    "debugging": {
        "providers": [
            ("openrouter", "google/gemma-4-26b-a4b-it:free"),
            ("cerebras", "gpt-oss-120b"),
        ],
    },

    "writing": {
        "providers": [
            ("nara", "claude-haiku-4.5"),
            ("google", "gemini-2.5-flash"),
            ("groq", "llama-3.3-70b-versatile"),
        ],
    },

    "summarize": {
        "providers": [
            ("google", "gemini-2.5-flash-lite"),
            ("groq", "llama-3.3-70b-versatile"),
        ],
    },

    "translate": {
        "providers": [
            ("google", "gemini-2.5-flash"),
            # nvidia/riva-translate-4b-instruct removed — confirmed dead
            # (404 "Function not found for account", 3/3 test calls failed)
        ],
    },

    "tamil": {
        "providers": [
            ("google", "gemini-2.5-flash"),
            ("groq", "llama-3.3-70b-versatile"),
        ],
    },

    "vision": {
        "providers": [
            ("google", "gemini-2.5-flash"),
        ],
    },

    "ocr": {
        "providers": [
            ("google", "gemini-2.5-flash"),
        ],
    },

    "document": {
        "providers": [
            ("google", "gemini-2.5-flash"),
        ],
    },

    "math": {
        "providers": [
            ("cerebras", "gpt-oss-120b"),
        ],
    },

    "embeddings": {
        "providers": [
            
        ],
    },

    "tool_calling": {
        "providers": [
            ("groq", "llama-3.3-70b-versatile"),
        ],
    },

    "medical": {
        "providers": [
            ("nara", "claude-haiku-4.5"),
        ],
    },

    "finance": {
        "providers": [
            ("nara", "claude-haiku-4.5"),
        ],
    },
}


OFFLINE_FIRST = False


def set_offline_first(enabled: bool):
    """Toggle Offline First policy — when True, local providers are
    always tried before any cloud provider, regardless of ranking
    scores. This is a policy override on top of Provider Ranking,
    not a replacement for it."""
    global OFFLINE_FIRST
    OFFLINE_FIRST = enabled


def get_candidates(capability: str):
    entry = CAPABILITIES.get(capability, CAPABILITIES["conversation"])
    providers = entry["providers"]
    if not OFFLINE_FIRST:
        return providers
    local = [p for p in providers if p[0] == "local"]
    cloud = [p for p in providers if p[0] != "local"]
    return local + cloud
