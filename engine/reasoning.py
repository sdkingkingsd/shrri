"""
Step-by-step reasoning + constraint verification for SHRRI.

IMPORTANT — what this actually is, stated plainly:
This is NOT "self-thinking" or genuine introspection. LLMs cannot accurately
report on their own internal process (confirmed directly in SHRRI's own
thinking_test.py results — see Test 3). What this DOES do, based on the
real, research-backed ReAct pattern: force the model to write out reasoning
BEFORE committing to a final answer, then explicitly re-check that answer
against the question's own stated constraints. This measurably improves
reliability on multi-step/logic problems — it does not create real
understanding underneath.
"""


REASONING_PROMPT_SUFFIX = """

Before answering, think through this step by step:
1. Restate the key constraints/facts given in the question.
2. Work through the logic explicitly, one step at a time.
3. State your tentative answer.
4. CHECK: re-read the constraints from step 1 — does your tentative answer
   actually satisfy every one of them? If not, revise it ONCE.
5. Give your final answer, with the verification check included.

CRITICAL RULES:
- Do step 4 (the check) only ONE time. Do not loop back and re-check again.
- Never repeat a sentence, list, or paragraph you have already written in this
  response. If you notice yourself about to repeat something, stop and move
  directly to your final answer instead.
- Keep your total response under 400 words.
"""


def detect_repetition_loop(text: str, min_repeats: int = 3) -> bool:
    """Detect if the model is stuck repeating the same paragraph/sentence.

    This is a hard, code-level safety net — not just a prompt instruction —
    since prompt instructions alone don't reliably stop a model already
    stuck in a repetition loop (confirmed by direct testing: the model
    repeated the same paragraph dozens of times despite no instruction
    telling it to do so).
    """
    # Split into chunks (paragraphs) and check if any chunk repeats too often
    chunks = [c.strip() for c in text.split("\n\n") if len(c.strip()) > 30]
    if not chunks:
        return False

    seen_counts = {}
    for c in chunks:
        seen_counts[c] = seen_counts.get(c, 0) + 1
        if seen_counts[c] >= min_repeats:
            return True
    return False


def truncate_at_first_repeat(text: str) -> str:
    """If a repetition loop is detected, cut the response at the point
    just before repetition starts, instead of returning the full garbage."""
    chunks = [c for c in text.split("\n\n") if c.strip()]
    seen = set()
    clean_chunks = []
    for c in chunks:
        key = c.strip()
        if key in seen:
            break
        seen.add(key)
        clean_chunks.append(c)
    result = "\n\n".join(clean_chunks).strip()
    return result if result else text[:500]


def needs_reasoning_mode(message: str, agent_category: str) -> bool:
    """Decide whether this message should go through the reasoning+verify path."""
    msg = message.strip().lower()

    # Explicit opt-in — always honored regardless of category
    if msg.startswith("think:") or msg.startswith("verify:"):
        return True

    # Auto-trigger for categories prone to multi-step reasoning errors
    if agent_category in ("research", "plan"):
        return True

    return False


def strip_trigger_prefix(message: str) -> str:
    """Remove 'think:' / 'verify:' prefix before sending to the model."""
    msg = message.strip()
    for prefix in ("think:", "verify:"):
        if msg.lower().startswith(prefix):
            return msg[len(prefix):].strip()
    return msg


def build_reasoning_prompt(message: str) -> str:
    """Wrap the user's message with the step-by-step + verify instruction."""
    return f"{message}\n{REASONING_PROMPT_SUFFIX}"
