# ─────────────────────────────────────────────
#  SHRRI — Hardcoded Free Models (July 2026)
#  Source: live API scan from your keys
# ─────────────────────────────────────────────

FREE_MODELS = {

    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "models": [
            "allam-2-7b",
            "meta-llama/llama-prompt-guard-2-86m",
            "whisper-large-v3",
            "canopylabs/orpheus-arabic-saudi",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "openai/gpt-oss-safeguard-20b",
            "qwen/qwen3.6-27b",
            "meta-llama/llama-prompt-guard-2-22m",
            "qwen/qwen3-32b",
            "openai/gpt-oss-20b",
            "llama-3.3-70b-versatile",
            "openai/gpt-oss-120b",
            "groq/compound",
            "canopylabs/orpheus-v1-english",
            "whisper-large-v3-turbo",
            "groq/compound-mini",
            "llama-3.1-8b-instant",
        ]
    },

    "cerebras": {
        "base_url": "https://api.cerebras.ai/v1",
        "models": [
            "gemma-4-31b",
            "zai-glm-4.7",
            "gpt-oss-120b",
        ]
    },

    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "models": [
            # ── General Chat ──────────────────────────
            "meta/llama-3.3-70b-instruct",
            "meta/llama-3.1-70b-instruct",
            "meta/llama-3.1-8b-instruct",
            "meta/llama-4-maverick-17b-128e-instruct",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "minimaxai/minimax-m2.7",
            "minimaxai/minimax-m3",
            "moonshotai/kimi-k2.6",
            "mistralai/mistral-large-3-675b-instruct-2512",
            "mistralai/mistral-nemotron",
            "mistralai/mistral-small-4-119b-2603",
            "mistralai/mistral-medium-3.5-128b",
            "mistralai/mistral-large-2-instruct",
            "mistralai/mistral-large",
            "mistralai/mixtral-8x22b-v0.1",
            "mistralai/mixtral-8x7b-instruct-v0.1",
            "mistralai/ministral-14b-instruct-2512",
            "mistralai/mistral-7b-instruct-v0.3",
            "qwen/qwen3-next-80b-a3b-instruct",
            "qwen/qwen3.5-122b-a10b",
            "qwen/qwen3.5-397b-a17b",
            "z-ai/glm-5.1",
            "stepfun-ai/step-3.5-flash",
            "stepfun-ai/step-3.7-flash",
            "bytedance/seed-oss-36b-instruct",
            "databricks/dbrx-instruct",
            "upstage/solar-10.7b-instruct",
            "01-ai/yi-large",
            "aisingapore/sea-lion-7b-instruct",
            "zyphra/zamba2-7b-instruct",
            "stockmark/stockmark-2-100b-instruct",
            "ai21labs/jamba-1.5-large-instruct",
            "nv-mistralai/mistral-nemo-12b-instruct",
            "nvidia/llama-3.1-nemotron-51b-instruct",
            "nvidia/llama-3.1-nemotron-70b-instruct",
            "nvidia/llama-3.1-nemotron-ultra-253b-v1",
            "nvidia/llama-3.3-nemotron-super-49b-v1",
            "nvidia/llama-3.3-nemotron-super-49b-v1.5",
            "nvidia/nemotron-3-super-120b-a12b",
            "nvidia/nemotron-3-ultra-550b-a55b",
            "nvidia/nemotron-3-nano-30b-a3b",
            "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
            "nvidia/nemotron-4-340b-instruct",
            "nvidia/nemotron-mini-4b-instruct",
            "nvidia/nemotron-nano-3-30b-a3b",
            "nvidia/nvidia-nemotron-nano-9b-v2",
            "nvidia/llama-3.1-nemotron-nano-8b-v1",
            "nvidia/cosmos-reason2-8b",
            "abacusai/dracarys-llama-3.1-70b-instruct",
            # ── Coding ────────────────────────────────
            "meta/codellama-70b",
            "deepseek-ai/deepseek-coder-6.7b-instruct",
            "deepseek-ai/deepseek-v4-flash",
            "deepseek-ai/deepseek-v4-pro",
            "google/codegemma-1.1-7b",
            "google/codegemma-7b",
            "ibm/granite-34b-code-instruct",
            "ibm/granite-8b-code-instruct",
            "bigcode/starcoder2-15b",
            "mistralai/codestral-22b-instruct-v0.1",
            "nvidia/nv-embedcode-7b-v1",
            # ── Vision / Multimodal ───────────────────
            "meta/llama-3.2-11b-vision-instruct",
            "meta/llama-3.2-90b-vision-instruct",
            "microsoft/phi-4-multimodal-instruct",
            "microsoft/phi-3-vision-128k-instruct",
            "nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
            "nvidia/nemotron-nano-12b-v2-vl",
            "google/diffusiongemma-26b-a4b-it",
            "adept/fuyu-8b",
            "microsoft/kosmos-2",
            "nvidia/vila",
            "nvidia/neva-22b",
            "nvidia/nvclip",
            "google/deplot",
            # ── Embeddings ────────────────────────────
            "baai/bge-m3",
            "nvidia/nv-embed-v1",
            "nvidia/nv-embedqa-e5-v5",
            "nvidia/nv-embedqa-mistral-7b-v2",
            "nvidia/llama-nemotron-embed-1b-v2",
            "nvidia/llama-nemotron-embed-vl-1b-v2",
            "nvidia/llama-3.2-nv-embedqa-1b-v1",
            "nvidia/embed-qa-4",
            "snowflake/arctic-embed-l",
            # ── Small / Efficient ─────────────────────
            "meta/llama-3.2-1b-instruct",
            "meta/llama-3.2-3b-instruct",
            "google/gemma-2b",
            "google/gemma-2-2b-it",
            "google/gemma-3-4b-it",
            "google/gemma-3-12b-it",
            "google/gemma-3n-e2b-it",
            "google/gemma-3n-e4b-it",
            "google/gemma-4-31b-it",
            "google/recurrentgemma-2b",
            "microsoft/phi-4-mini-instruct",
            "microsoft/phi-3.5-moe-instruct",
            "ibm/granite-3.0-3b-a800m-instruct",
            "ibm/granite-3.0-8b-instruct",
            "nvidia/llama-3.1-nemotron-nano-8b-v1",
            "nvidia/mistral-nemo-minitron-8b-8k-instruct",
            # ── Specialised ───────────────────────────
            "sarvamai/sarvam-m",               # Indic languages
            "nvidia/riva-translate-4b-instruct",  # translation
            "nvidia/riva-translate-4b-instruct-v1.1",
            "writer/palmyra-fin-70b-32k",      # finance
            "writer/palmyra-med-70b",          # medical
            "writer/palmyra-med-70b-32k",
            "writer/palmyra-creative-122b",    # creative writing
            "nvidia/nemotron-4-340b-reward",   # reward model
            "meta/llama-guard-4-12b",          # safety
            "nvidia/llama-3.1-nemoguard-8b-content-safety",
            "nvidia/nemotron-3-content-safety",
            "nvidia/nemotron-content-safety-reasoning-4b",
            "nvidia/gliner-pii",               # PII detection
            "nvidia/nemoretriever-parse",      # document parsing
            "nvidia/nemotron-parse",
            "nvidia/llama-3.2-nemoretriever-1b-vlm-embed-v1",
        ]
    },

    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "models": [
            # ── General ───────────────────────────────
            "openai/gpt-oss-120b:free",
            "openai/gpt-oss-20b:free",
            "meta-llama/llama-3.3-70b-instruct:free",
            "meta-llama/llama-3.2-3b-instruct:free",
            "nousresearch/hermes-3-llama-3.1-405b:free",
            "qwen/qwen3-next-80b-a3b-instruct:free",
            "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            # ── Coding ────────────────────────────────
            "qwen/qwen3-coder:free",
            "poolside/laguna-m.1:free",
            "poolside/laguna-xs.2:free",
            "cohere/north-mini-code:free",
            # ── Vision ────────────────────────────────
            "nvidia/nemotron-nano-12b-v2-vl:free",
            # ── Small / Fast ──────────────────────────
            "liquid/lfm-2.5-1.2b-instruct:free",
            "liquid/lfm-2.5-1.2b-thinking:free",
            "google/gemma-4-26b-a4b-it:free",
            "google/gemma-4-31b-it:free",
            # ── Nvidia via OpenRouter ─────────────────
            "nvidia/nemotron-3-ultra-550b-a55b:free",
            "nvidia/nemotron-3-super-120b-a12b:free",
            "nvidia/nemotron-3-nano-30b-a3b:free",
            "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
            "nvidia/nemotron-nano-9b-v2:free",
            "nvidia/nemotron-3.5-content-safety:free",
        ]
    },

    "google": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "models": [
            "models/gemini-2.5-flash",
            "models/gemini-2.5-flash-lite",
            "models/gemini-3-flash-preview",
            "models/gemini-3.1-flash-lite",
            "models/gemma-4-26b-a4b-it",
            "models/gemma-4-31b-it",
            "models/gemini-embedding-001",
        ]
    },

    "nara": {
        "base_url": "https://router.bynara.id/v1",
        "models": [
            # ── Included in Free Plan (6 models) ─────
            "mimo-v2.5-free",       # Vision, 1M ctx
            "mimo-v2.5-pro-free",   # Text, 1M ctx, 5x multiplier
            "mistral-large",        # Text, 252K ctx
            "mistral-medium-3-5",   # Vision, 256K ctx
            "claude-sonnet-4.5",    # Vision, 200K ctx, 3x multiplier
            "claude-haiku-4.5",     # Vision, 200K ctx
        ]
    },

}

# ── Quick stats ───────────────────────────────────────
if __name__ == "__main__":
    total = 0
    for provider, info in FREE_MODELS.items():
        count = len(info["models"])
        total += count
        print(f"{provider:12} → {count} models")
    print(f"{'─'*30}")
    print(f"{'TOTAL':12} → {total} models")
