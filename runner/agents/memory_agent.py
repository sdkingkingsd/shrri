"""
Memory Agent — SHRRI AI OS v2 (Phase 5)

Specialist agent for remember/recall tasks. Thin wrapper around the
existing engine.memory.Memory singleton — no new storage logic here,
just routing a natural-language request to the right Memory method
and letting the LLM phrase a clean reply.

Handles three intents, decided heuristically from the prompt text:
  - "remember ..." / "note that ..."   -> save_fact via extractor-style split
  - "what do you know about ..." / "recall ..." -> search + get_all_facts lookup
  - anything else                       -> search conversations + facts, then
                                            let the LLM summarize the findings
"""

import re
from engine.router import Router
from engine.memory import Memory

_MEMORY_SYSTEM_PROMPT = (
    "You are a memory specialist. You are given raw facts and/or past "
    "conversation snippets retrieved from long-term storage. Answer the "
    "user's request using ONLY that retrieved information. If nothing "
    "relevant was retrieved, say so plainly instead of guessing."
)

_REMEMBER_PATTERNS = [
    r"^remember (that )?(?P<rest>.+)$",
    r"^note (that )?(?P<rest>.+)$",
    r"^save (this|that)?:?\s*(?P<rest>.+)$",
]


class MemoryAgent:
    def __init__(self, verbose: bool = False):
        self._router = Router()
        self._memory = Memory()
        self.verbose = verbose

    def _try_remember(self, prompt: str):
        low = prompt.strip().lower()
        for pat in _REMEMBER_PATTERNS:
            m = re.match(pat, low)
            if m:
                rest = prompt.strip()[m.start("rest"):]
                # Split "X is Y" / "X = Y" into key/value; else use a
                # generic key so it's still retrievable via search.
                kv = re.match(r"^(?P<key>.{1,60}?)\s+(?:is|=|:)\s+(?P<val>.+)$", rest)
                if kv:
                    key, val = kv.group("key").strip(), kv.group("val").strip()
                else:
                    key, val = f"note_{abs(hash(rest)) % 100000}", rest.strip()
                return key, val
        return None

    def run(self, payload: dict) -> str:
        prompt = payload.get("prompt", "")
        if self.verbose:
            print(f"[memory_agent] Handling: {prompt[:80]!r}")

        remember = self._try_remember(prompt)
        if remember:
            key, val = remember
            ok = self._memory.save_fact(key, val)
            if ok is False:
                return f"GAP: couldn't save that to memory (blocked by safety filter)."
            if self.verbose:
                print(f"[memory_agent] Saved fact '{key}' = {val!r}")
            return f"Got it — I'll remember that {key} is {val}."

        # Recall / search path
        facts = self._memory.get_all_facts()
        convo_hits = self._memory.search(prompt)

        context_parts = []
        if facts:
            fact_lines = "\n".join(f"- {k}: {v}" for k, v in facts.items())
            context_parts.append(f"Stored facts:\n{fact_lines}")
        if convo_hits:
            convo_lines = "\n".join(f"- ({h['role']}) {h['content']}" for h in convo_hits)
            context_parts.append(f"Matching past conversation snippets:\n{convo_lines}")

        if not context_parts:
            return "I don't have anything relevant stored in memory for that."

        context = "\n\n".join(context_parts)
        full_prompt = f"Retrieved memory:\n{context}\n\nUser request: {prompt}"

        response = self._router.chat(
            full_prompt,
            system=_MEMORY_SYSTEM_PROMPT,
            capability="reasoning",
        )

        if not response or not response.strip():
            raise RuntimeError("Memory agent got an empty response from all providers")

        return response
