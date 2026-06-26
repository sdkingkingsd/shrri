import sys
sys.path.insert(0, '/home/shrridharshan/shrri')

from .key_manager import KeyManager
from .providers import (
    GroqProvider,
    CerebrasProvider,
    NvidiaProvider,
    OllamaProvider
)

PROVIDER_PRIORITY = ["groq", "cerebras", "nvidia", "ollama"]

TASK_ROUTING = {
    "fast":     ["groq", "cerebras", "ollama"],
    "long":     ["nvidia", "groq", "ollama"],
    "code":     ["nvidia", "groq", "cerebras", "ollama"],
    "reason":   ["nvidia", "groq", "ollama"],
    "default":  ["groq", "cerebras", "nvidia", "ollama"],
}


def _get_search_context(message: str) -> str:
    try:
        from tools.search import smart_search
        result = smart_search(message)
        return result
    except Exception as e:
        print(f"[SHRRI] Search tool error: {e}")
        return ""


def _classify_intent_llm(message: str) -> str:
    """Ask the AI which tool this message needs, when keyword matching finds nothing."""
    try:
        system = (
            "You are an intent classifier for a personal assistant called SHRRI. "
            "Reply with ONLY one word from this exact list, nothing else:\n"
            "whatsapp_read, whatsapp_send, email, calendar, notes, files, "
            "youtube, weather, pyexec, system, none\n"
            "Pick whatsapp_read for anything about checking/reading WhatsApp. "
            "Pick whatsapp_send only if they want to send a message. "
            "If nothing matches, reply: none"
        )
        router = Router()
        result = router.chat(message, task="fast", system=system, web_search=False)
        if not result:
            return "none"
        return result.strip().lower().split()[0].strip(".,!")
    except Exception as e:
        print(f"[SHRRI] Intent classifier error: {e}")
        return "none"

_FALLBACK_MAP = {
    "whatsapp_read": ("wa_read", "read"),
    "whatsapp_send": ("whatsapp", "send"),
    "email": ("email", "check"),
    "calendar": ("calendar", "check"),
    "notes": ("notes", "show"),
    "files": ("files", "search"),
    "youtube": ("youtube", "summarize"),
    "weather": ("weather", "check"),
    "pyexec": ("pyexec", "run"),
    "system": ("system", "control"),
}

def _get_tool_context(message: str) -> str:
    try:
        from tools.dispatcher import detect_intent, run_tool
        intent = detect_intent(message)
        if intent["tool"] != "none":
            pass  # silent tool trigger
            return run_tool(intent, message)
        # Fallback: keyword match found nothing — ask the AI what's needed
        guessed = _classify_intent_llm(message)
        if guessed in _FALLBACK_MAP:
            tool, action = _FALLBACK_MAP[guessed]
            print(f"[SHRRI] AI fallback routed to: {tool}")
            fallback_intent = {"tool": tool, "action": action, "params": {"query": message}}
            return run_tool(fallback_intent, message)
        return ""
    except Exception as e:
        print(f"[SHRRI] Tool dispatcher error: {e}")
        return ""


class Router:
    def __init__(self):
        self.km = KeyManager()

    def _get_provider(self, provider_name, api_key):
        if provider_name == "groq":
            return GroqProvider(api_key)
        elif provider_name == "cerebras":
            return CerebrasProvider(api_key)
        elif provider_name == "nvidia":
            base_url = self.km.get_base_url("nvidia")
            return NvidiaProvider(api_key, base_url)
        elif provider_name == "ollama":
            base_url = self.km.get_base_url("ollama") or "http://localhost:11434"
            return OllamaProvider(base_url)
        return None

    def chat(self, message, task="default", history=None, system=None, web_search=True):
        priority = TASK_ROUTING.get(task, TASK_ROUTING["default"])

        context = ""
        if web_search:
            # Tool dispatcher first (Gmail, Calendar, etc.)
            context = _get_tool_context(message)
            # Web search only if no tool handled it
            if not context:
                context = _get_search_context(message)
                if context:
                    pass  # silent search

        if context:
            # Math/time results are authoritative — the LLM must NOT re-derive them.
            # Gmail/search results are reference context — the LLM should summarize them.
            is_authoritative = context.startswith("🧮") or context.startswith("Current time:")
            if is_authoritative:
                label = "[Authoritative answer from deterministic tool — state this result directly, do NOT recalculate or re-derive]"
            else:
                label = "[Live Data — use this to answer accurately]"
            enriched_message = (
                f"{message}\n\n"
                f"{label}:\n"
                f"{context}"
            )
        else:
            enriched_message = message

        

        for provider_name in priority:
            try:
                if provider_name == "ollama":
                    model = self.km.get_model("ollama")
                    base_url = self.km.get_base_url("ollama") or "http://localhost:11434"
                    provider = OllamaProvider(base_url)
                    response = provider.chat(enriched_message, model, history=history, system=system)
                    print(f"[SHRRI] Used: ollama ({model})")
                    return response

                tried_ids = set()

                while True:
                    api_key, key_id = self.km.get_best_key(provider_name, exclude_ids=tried_ids)
                    if not api_key or api_key.startswith("YOUR_"):
                        break

                    model = self.km.get_model(provider_name, task)
                    if not model:
                        model = self.km.get_model(provider_name)

                    provider = self._get_provider(provider_name, api_key)
                    if not provider:
                        break

                    try:
                        response = provider.chat(enriched_message, model, history=history, system=system)
                        self.km.mark_used(key_id)
                        pass  # silent provider
                        return response
                    except Exception as e:
                        if "rate_limit" in str(e).lower() or "429" in str(e):
                            pass  # silent rate limit — just failover
                        else:
                            print(f"[SHRRI] {provider_name} key {key_id} failed: {e} — trying next key...")
                        self.km.mark_cooldown(key_id, seconds=60)
                        tried_ids.add(key_id)
                        continue

            except Exception as e:
                print(f"[SHRRI] {provider_name} failed: {e} — trying next provider...")
                continue

        return "ERROR: All providers failed. Check your keys and internet connection."

    def status(self):
        return self.km.get_status()
