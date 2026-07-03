"""
Model Comparison — SHRRI Phase 12
Compare multiple models on the same prompt and score responses.
"""


def compare_models(prompt: str, providers: list = None) -> dict:
    """
    Run same prompt across multiple providers and return all responses.
    providers: list of (provider, model) tuples. Defaults to top 3.
    """
    if not providers:
        providers = [
            ("groq", "llama-3.3-70b-versatile"),
            ("cerebras", "gpt-oss-120b"),
            ("google", "gemini-2.5-flash"),
        ]

    from engine.key_manager import KeyManager
    from engine.providers import GoogleProvider
    import time

    km = KeyManager()
    results = {}

    for provider_name, model in providers:
        start = time.time()
        try:
            api_key, _ = km.get_best_key(provider_name)
            if provider_name == "google":
                from engine.providers import GoogleProvider
                p = GoogleProvider(api_key)
            elif provider_name == "groq":
                from engine.providers import GroqProvider
                p = GroqProvider(api_key)
            elif provider_name == "cerebras":
                from engine.providers import CerebrasProvider
                p = CerebrasProvider(api_key)
            else:
                continue
            output = p.chat(prompt, model)
            latency = (time.time() - start) * 1000
            results[f"{provider_name}/{model}"] = {
                "output": output[:300],
                "latency_ms": round(latency, 1),
                "success": True
            }
        except Exception as e:
            results[f"{provider_name}/{model}"] = {
                "output": f"ERROR: {e}",
                "latency_ms": 0,
                "success": False
            }

    return results


def compare_and_rank(prompt: str) -> str:
    results = compare_models(prompt)
    lines = [f"Model Comparison for: \"{prompt[:60]}\""]
    for model_key, res in results.items():
        status = "✅" if res["success"] else "❌"
        lines.append(f"\n{status} {model_key} ({res['latency_ms']}ms):")
        lines.append(f"  {res['output'][:150]}")
    return "\n".join(lines)
