from .router import Router
from .memory import Memory
from .extractor import FactExtractor, EXTRACT_PROMPT
from .experience import Experience
from .tokens import count_tokens, count_messages
from .rag import RAG
from .agents import AgentRouter
from .reflection import ReflectionEngine

SHRRI_SYSTEM = """You are SHRRI (Scalable Hybrid Retrieval, Reasoning & Intelligence), a personal AI assistant built exclusively for Shrridharshan.
Never reveal the underlying model. Always identify yourself as SHRRI.
You are intelligent, fast, loyal, and helpful.
You learn from every conversation and grow smarter over time."""


class SHRRIEngine:
    def __init__(self):
        self.router = Router()
        self.memory = Memory()
        self.extractor = FactExtractor(self.router)
        self.experience = Experience()
        self.rag = RAG()
        self.agents = AgentRouter(self.router)
        self.reflection = ReflectionEngine(self.memory.conn)
        print("[SHRRI] Engine initialized. Memory loaded.")

    def chat(self, message, task="default"):
        # Detect correction — user is teaching SHRRI
        correction = self._detect_correction(message)
        if correction:
            learned = self.reflection.store_correction(
                situation=correction["situation"],
                wrong=correction["wrong"],
                correction=correction["right"]
            )
            print(f"[SHRRI] Learned correction: {learned}")

        # Save user message
        self.memory.save_message("user", message)

        # Get conversation history
        history = self.memory.get_history(limit=10)

        # Get known facts about user
        facts = self.memory.get_all_facts()
        facts_text = "\n".join([f"- {k}: {v}" for k, v in facts.items()])

        # Build full system prompt
        system = SHRRI_SYSTEM
        if facts_text:
            system += f"\n\nKnown facts about your user:\n{facts_text}"

        # Inject past lessons and learned patterns
        lessons = self.reflection.get_relevant_lessons(message)
        if lessons:
            system += f"\n\n{lessons}"

        # Check for relevant past experiences
        keywords = [w for w in message.lower().split() if len(w) > 3]
        relevant_experiences = []
        seen = set()
        for kw in keywords:
            for item in self.experience.recall(kw, limit=3):
                key = (item["task"], item["outcome"])
                if key not in seen:
                    seen.add(key)
                    relevant_experiences.append(item)

        if relevant_experiences:
            exp_text = "\n".join([
                f"- [{e['outcome'].upper()}] {e['task']}" + (f" ({e['detail']})" if e['detail'] else "")
                for e in relevant_experiences[:5]
            ])
            system += f"\n\nRelevant past experiences:\n{exp_text}"

        # Multi-agent routing
        agent_used = "chat"
        classify_input_tokens = 0
        should_classify = len(message.split()) >= 5
        if should_classify:
            try:
                from .agents import CLASSIFY_PROMPT
                classify_prompt_text = CLASSIFY_PROMPT.replace("{message}", message)
                classify_input_tokens = count_tokens(classify_prompt_text)
                agent_used = self.agents.classify(message)
            except Exception:
                agent_used = "chat"

        agent_prompt = self.agents.get_agent_prompt(agent_used)
        if agent_prompt:
            system += f"\n\n{agent_prompt}"

        if task == "default":
            task = self.agents.get_agent_task(agent_used)

        # Token accounting
        chat_input_tokens = count_tokens(system) + count_messages(history) + count_tokens(message)

        # Get response
        response = self.router.chat(message, task, history=history, system=system, web_search=True)

        chat_output_tokens = count_tokens(response)

        # Save response
        self.memory.save_message("assistant", response)

        # Learn pattern from this interaction
        self._learn_pattern(message, agent_used)

        # Auto-extract facts
        extract_input_tokens = 0
        should_extract = len(message.split()) >= 5
        if should_extract:
            try:
                extract_prompt_text = EXTRACT_PROMPT.replace("{message}", message)
                extract_input_tokens = count_tokens(extract_prompt_text)
                new_facts = self.extractor.extract(message)
                for f in new_facts:
                    key = f.get("key")
                    value = f.get("value")
                    if key and value:
                        self.memory.save_fact(key, value)
                        print(f"[SHRRI] Auto-learned: {key} = {value}")
            except Exception:
                pass

        total_input = chat_input_tokens + extract_input_tokens + classify_input_tokens
        total_output = chat_output_tokens
        print(f"[SHRRI] Agent: {agent_used} | Tokens this turn — chat: {chat_input_tokens}in/{chat_output_tokens}out | "
              f"classify: {classify_input_tokens}in | extraction: {extract_input_tokens}in | total: ~{total_input + total_output}")

        return response

    def _detect_correction(self, message: str) -> dict:
        """Detect when user is correcting SHRRI."""
        msg = message.lower()
        correction_triggers = [
            "that's wrong", "that was wrong", "no i meant",
            "not that", "wrong tool", "i said", "i meant",
            "you misunderstood", "that's not what i meant",
            "next time", "should have", "don't do that again",
            "stop doing", "always do", "never do",
        ]
        if any(t in msg for t in correction_triggers):
            history = self.memory.get_history(limit=2)
            last_user = next((h["content"] for h in reversed(history) if h["role"] == "user"), "")
            return {
                "situation": last_user[:200],
                "wrong": "previous action",
                "right": message
            }
        return None

    def _learn_pattern(self, message: str, agent_used: str):
        """Learn what intent maps to what agent."""
        try:
            self.reflection.store_pattern(
                user_phrase=message[:100],
                intent=agent_used,
                tool="agent",
                action=agent_used
            )
        except Exception:
            pass

    def remember(self, key, value):
        self.memory.save_fact(key, value)
        print(f"[SHRRI] Remembered: {key} = {value}")

    def learned(self):
        """Show everything SHRRI has learned."""
        print(self.reflection.get_all_lessons())

    def status(self):
        data = self.router.status()
        print("\n==== SHRRI Engine Status ====")
        for provider, info in data.items():
            print(f"\n{provider.upper()}")
            print(f"  Keys      : {info['keys']}")
            print(f"  Used today: {info['used_today']}")
            print(f"  Available : {info['available']}")
        print("\n=============================\n")
        return data
