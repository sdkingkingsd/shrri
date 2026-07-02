# config/capability_map.py
"""
Each capability maps to an ORDERED list of (provider, model) candidates.
Router tries them in order until one succeeds.
"""

CAPABILITIES = {

    "conversation": {
        "providers": [
            ("groq", "llama-3.3-70b-versatile"),
            ("google", "gemini-2.5-flash"),
            ("nara", "claude-haiku-4.5"),
            ("cerebras", "gpt-oss-120b"),
            ("local", "qwen2.5:3b"),
        ],
    },

    "reasoning": {
        "providers": [
            ("nvidia", "nvidia/llama-3.3-nemotron-super-49b-v1"),
            ("cerebras", "gpt-oss-120b"),
            ("google", "gemini-2.5-flash"),
            ("local", "qwen2.5:3b"),
        ],
    },

    "coding": {
        "providers": [
            
            ("nvidia", "meta/llama-3.1-8b-instruct"),
            ("openrouter", "google/gemma-4-26b-a4b-it:free"),
            ("groq", "llama-3.3-70b-versatile"),
            ("local", "qwen2.5-coder:7b"),
        ],
    },

    "debugging": {
        "providers": [
            ("nvidia", "meta/llama-3.1-8b-instruct"),
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
            ("nvidia", "meta/llama-3.1-8b-instruct"),
        ],
    },

    "translate": {
        "providers": [
            ("nvidia", "nvidia/riva-translate-4b-instruct"),
            ("google", "gemini-2.5-flash"),
            ("nvidia", "sarvamai/sarvam-m"),
        ],
    },

    "tamil": {
        "providers": [
            ("nvidia", "sarvamai/sarvam-m"),
            ("google", "gemini-2.5-flash"),
            ("groq", "llama-3.3-70b-versatile"),
        ],
    },

    "vision": {
        "providers": [
            ("nvidia", "meta/llama-3.2-11b-vision-instruct"),
            ("google", "gemini-2.5-flash"),
        ],
    },

    "ocr": {
        "providers": [
            ("nvidia", "nvidia/nemoretriever-parse"),
            ("google", "gemini-2.5-flash"),
        ],
    },

    "document": {
        "providers": [
            ("nvidia", "nvidia/nemoretriever-parse"),
            ("google", "gemini-2.5-flash"),
        ],
    },

    "math": {
        "providers": [
            ("cerebras", "gpt-oss-120b"),
            ("nvidia", "nvidia/llama-3.3-nemotron-super-49b-v1"),
        ],
    },

    "embeddings": {
        "providers": [
            ("nvidia", "nvidia/nv-embed-v1"),
            
        ],
    },

    "tool_calling": {
        "providers": [
            ("nvidia", "nvidia/mistral-nemotron"),
            ("groq", "llama-3.3-70b-versatile"),
        ],
    },

    "medical": {
        "providers": [
            ("nvidia", "writer/palmyra-med-70b"),
            ("nara", "claude-haiku-4.5"),
        ],
    },

    "finance": {
        "providers": [
            ("nvidia", "writer/palmyra-fin-70b-32k"),
            ("nara", "claude-haiku-4.5"),
        ],
    },
}


def get_candidates(capability: str):
    entry = CAPABILITIES.get(capability, CAPABILITIES["conversation"])
    return entry["providers"]
