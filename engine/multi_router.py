# engine/multi_router.py
from engine.key_manager import KeyManager
from engine.provider_registry import registry
from config.capability_map import get_candidates

km = KeyManager()

import time
from runner.provider_ranking import ProviderRanking

_ranking = ProviderRanking()


def route(capability: str, prompt: str, verbose=False):
    candidates = get_candidates(capability)
    candidates = _ranking.rank_candidates(candidates)
    last_error = None

    for provider_name, model in candidates:
        if provider_name == "local":
            key, key_id = "local", "local"
        else:
            key, key_id = km.get_best_key(provider_name)
            if key is None:
                if verbose:
                    print(f"⏭️  {provider_name} exhausted/no key, skipping")
                continue

        try:
            if verbose:
                print(f"🔹 Trying {provider_name} / {model}")
            provider = registry.get_instance(provider_name, key)
            _t0 = time.time()
            response = provider.chat(prompt, model)
            _latency = time.time() - _t0

            if key_id != "local":
                km.mark_used(key_id)

            _ranking.record(provider_name, model, success=True, latency_seconds=_latency)

            return {
                "provider": provider_name,
                "model": model,
                "response": response,
                "success": True,
            }
        except Exception as e:
            last_error = e
            _ranking.record(provider_name, model, success=False)
            if verbose:
                print(f"❌ {provider_name} failed: {e}")
            continue

    return {
        "provider": None,
        "model": None,
        "response": None,
        "success": False,
        "error": str(last_error),
    }
