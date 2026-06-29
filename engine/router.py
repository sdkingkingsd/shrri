import sys
sys.path.insert(0, '/home/shrridharshan/shrri')

from .key_manager import KeyManager
from .providers import (
    GroqProvider,
    CerebrasProvider,
    NvidiaProvider,
    OllamaProvider,
    TempLLMProvider
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
    """Ask the AI which tool+action this message needs, when keyword matching finds nothing."""
    try:
        system = (
            "You are an intent classifier for a personal assistant called SHRRI. "
            "Reply with ONLY one label from this exact list, nothing else, no explanation:\n"
            "math, time, gmail_read, gmail_send, gmail_search, whatsapp_read, whatsapp_send, "
            "briefing, pyexec, youtube, files, system, notes_save, notes_show, notes_delete, "
            "reminder_set, reminder_list, calendar_create, calendar_today, calendar_upcoming, "
            "weather, none\n\n"
            "Guidance:\n"
            "- whatsapp_read: checking/reading WhatsApp messages, any phrasing, any language\n"
            "- whatsapp_send: sending a WhatsApp message to someone\n"
            "- gmail_read: checking/reading email inbox\n"
            "- gmail_send: sending an email\n"
            "- gmail_search: searching for a specific email\n"
            "- notes_save: asking to save/remember/note something\n"
            "- notes_show: asking to see saved notes\n"
            "- notes_delete: asking to delete/remove a note\n"
            "- reminder_set: asking to be reminded of something at a time\n"
            "- reminder_list: asking what reminders are set\n"
            "- calendar_create: asking to add an event/meeting\n"
            "- calendar_today: asking what's on today's calendar\n"
            "- calendar_upcoming: asking about upcoming days/week\n"
            "- briefing: ONLY for explicit daily-briefing requests like \"good morning\", "
            "\"give me my briefing\", \"what's my day look like\" — NOT for personal questions "
            "like \"tell me about me\" or \"what do you know about me\", which are 'none' "
            "(those go straight to the assistant's normal reply using saved facts)\n"
            "- pyexec: asking to run/calculate something with code\n"
            "- youtube: asking to summarize a video\n"
            "- files: asking to find/search files\n"
            "- system: asking to control volume/brightness/lock screen\n"
            "- weather: asking about weather\n"
            "- math/time: only if no other category fits, simple calculation or current time\n"
            "- none: casual conversation, general questions, personal questions like "
            "\"tell me about me\", \"what do you know about me\", \"who am I\" — these "
            "should NOT trigger any tool, the assistant already knows saved facts and answers "
            "directly. Also use 'none' for anything not clearly matching another label.\n"
            "If unsure, prefer none over guessing wrong."
        )
        router = Router()
        result = router.chat(message, task="fast", system=system, web_search=False)
        if not result:
            return "none"
        return result.strip().lower().split()[0].strip(".,!")
    except Exception as e:
        print(f"[SHRRI] Intent classifier error: {e}")
        return "none"

# Maps classifier label -> (tool, action). Must match run_tool()'s expectations exactly.
_FALLBACK_MAP = {
    "math":              ("math", "calculate"),
    "time":              ("time", "get_time"),
    "gmail_read":        ("gmail", "read"),
    "gmail_send":        ("gmail", "send"),
    "gmail_search":      ("gmail", "search"),
    "whatsapp_read":     ("wa_read", "read"),
    "whatsapp_send":     ("whatsapp", "send"),
    "briefing":          ("briefing", "get"),
    "pyexec":            ("pyexec", "run"),
    "youtube":           ("youtube", "summarize"),
    "files":             ("files", "search"),
    "system":            ("system", "control"),
    "notes_save":        ("notes", "save"),
    "notes_show":        ("notes", "show"),
    "notes_delete":      ("notes", "delete"),
    "reminder_set":      ("reminder", "set"),
    "reminder_list":     ("reminder", "list"),
    "reminder_delete":   ("reminder", "delete_all"),
    "calendar_create":   ("calendar", "create"),
    "calendar_today":    ("calendar", "today"),
    "calendar_date":     ("calendar", "date"),
    "calendar_upcoming": ("calendar", "upcoming"),
    "weather":           ("weather", "get"),
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
            print(f"[SHRRI] AI fallback routed to: {tool} ({action})")
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
            is_authoritative = context.startswith("🧮") or context.startswith("Current time:") or context.startswith("Screenshot saved") or context.startswith("Browser error") or context.startswith("✅")
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
                        # Treat empty/placeholder output as a failure, not a real answer —
                        # some models occasionally return blank content + blank reasoning,
                        # which providers.py turns into the literal string "No response".
                        if not response or not response.strip() or response.strip() == "No response":
                            print(f"[SHRRI] {provider_name} key {key_id} returned empty output — trying next key...")
                            self.km.mark_cooldown(key_id, seconds=60)
                            tried_ids.add(key_id)
                            continue
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

        # All 4 providers failed — try templlm (ChatGPT via browser) as last resort
        try:
            templlm = TempLLMProvider()
            if templlm.is_available():
                print("[SHRRI] All providers failed — falling back to templlm (ChatGPT)")
                return templlm.chat(message)
            else:
                print("[SHRRI] templlm not available — starting it...")
                import subprocess
                subprocess.Popen(["templlm", "status"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                import time; time.sleep(5)
                if templlm.is_available():
                    return templlm.chat(message)
        except Exception as e:
            print(f"[SHRRI] templlm fallback failed: {e}")
        return "ERROR: All providers failed. Check your keys and internet connection."

    def status(self):
        return self.km.get_status()
