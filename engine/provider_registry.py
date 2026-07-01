from engine.providers import (
    GroqProvider, CerebrasProvider, NvidiaProvider,
    OpenRouterProvider, GoogleProvider, NaraProvider, OllamaProvider
)
from engine.key_manager import KeyManager

km = KeyManager()

class ProviderRegistry:
    def __init__(self):
        self._instances = {}

    def get_instance(self, name: str, key: str):
        cache_key = f"{name}:{key[:8] if key else 'local'}"
        if cache_key not in self._instances:
            self._instances[cache_key] = self._build(name, key)
        return self._instances[cache_key]

    def _build(self, name, key):
        if name == "groq":
            return GroqProvider(key)
        elif name == "cerebras":
            return CerebrasProvider(key)
        elif name == "nvidia":
            return NvidiaProvider(key, "https://integrate.api.nvidia.com/v1")
        elif name == "openrouter":
            return OpenRouterProvider(key)
        elif name == "google":
            return GoogleProvider(key)
        elif name == "nara":
            base_url = km.get_base_url("nara") if hasattr(km, "get_base_url") else None
            return NaraProvider(key, base_url)
        elif name == "local":
            base_url = km.get_base_url("ollama") if hasattr(km, "get_base_url") else "http://localhost:11434"
            return OllamaProvider(base_url)
        else:
            raise ValueError(f"Unknown provider: {name}")

registry = ProviderRegistry()
