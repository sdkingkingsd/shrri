"""
Agentic loop for SHRRI — handles multi-step and conditional requests.

Unlike the single-shot path in client.py (classify once, run once, reply),
this breaks a complex request into steps, executes them one at a time using
the EXISTING tool dispatcher, checks results after each step, and decides
whether to continue — enabling "if X then Y" and "do A, B, then C" requests.

Kept deliberately simple: no new tools, no new state machine framework.
Just a loop around what already exists, with a safety cap on steps.
"""

import json
import re

MAX_STEPS = 5
STEP_TIMEOUT_HINT = "Keep your plan to at most 5 steps."


def looks_multi_step(message: str) -> bool:
    """Cheap heuristic: does this message likely need the agentic loop?
    Kept conservative so simple chats don't pay the extra LLM calls."""
    msg = message.lower()
    if len(message.split()) < 6:
        return False
    multi_signals = [
        " if ", " then ", "and then", "after that",
        "check.*and", "first ", "next ", "followed by",
    ]
    conjunction_count = msg.count(" and ") + msg.count(" then ") + msg.count(", ")
    starts_with_if = msg.strip().startswith("if ")
    has_if_anywhere = " if " in msg or starts_with_if
    has_conditional = has_if_anywhere and (" then " in msg or msg.count(",") >= 1 or " send " in msg or " do " in msg)
    has_sequence_words = any(w in msg for w in ["first", "then", "after that", "followed by", "once you", "next "])
    return has_conditional or (has_sequence_words and conjunction_count >= 1) or conjunction_count >= 2


def plan_steps(message: str, router) -> list:
    """Ask the LLM to break the request into a numbered list of concrete steps.
    Each step should be phrased as a standalone instruction that the existing
    single-shot tool dispatcher can understand on its own."""
    prompt = f"""Break this user request into the MINIMUM number of concrete steps needed.

STRICT RULES:
- If the request is conditional ("if X, do Y"), output EXACTLY 2 steps — NEVER 3, NEVER MORE:
  1. "Check: <condition>"  — ONE step covering the ENTIRE condition, even if the
     condition has multiple parts (e.g. "unread AND from a specific sender" must be
     combined into ONE check, like "Check: there is an unread email from Cerebras" —
     NOT split into "check for unread emails" + "check for emails from Cerebras").
     CRITICAL — preserve negation exactly: if the user said "if I DON'T have X" or
     "if there are NO X", the Check: step must say "Check: I have NO X" or
     "Check: there are NO X" — NEVER drop the "no/don't/none" and flip the logic.
     The "If true:" action fires when the Check: condition is TRUE, so a negated
     condition ("Check: I have NO reminders") correctly gates the action only when
     there really are none.
  2. "If true: <action>"   (the action step MUST start with literally "If true:")
- Every step other than the final action step MUST start with literally "Check:" —
  never "If true: check ..." or "If true: look for ...". Only the LAST step may start
  with "If true:", and only if it performs the actual requested action (send, set,
  create, delete, reply, mark, archive, etc.) — never another check.
- If the request is NOT conditional, output steps with no "Check:"/"If true:" prefixes at all.
- Never emit both a generic gather-info step AND a separate "Check: <condition>" step for the same fact.
{STEP_TIMEOUT_HINT}

Request: "{message}"

- The action in step 2 (or the final step) MUST match the actual action verb in the
  original request — do NOT substitute a different action (e.g. if the user asked to
  "remind" or "set a reminder", the action step must say "set a reminder", NOT
  "send a WhatsApp message" or anything else). Preserve the user's original intent exactly.

Reply ONLY as JSON list of strings, nothing else (2 steps for conditional requests). The
examples below show STRUCTURE only — your action step must use the ACTUAL action requested,
not copy these examples literally:
["Check: <condition>", "If true: <the specific action the user actually asked for>"]
"""
    try:
        raw = router.chat(prompt, task="fast", web_search=False)
        raw = re.sub(r"^```json|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        steps = json.loads(raw)
        # Post-process: if the original message has a negated condition but the
        # planner dropped the negation from the Check: step, re-insert it.
        # This is deterministic Python, not another LLM call.
        if steps and steps[0].startswith("Check:"):
            _neg_phrases = [
                ("if i don't have", "NO"),
                ("if i dont have", "NO"),
                ("if there are no ", "NO"),
                ("if there is no ", "NO"),
                ("if i have no ", "NO"),
                ("if i haven't", "NO"),
                ("if i havent", "NO"),
                ("if i do not have", "NO"),
                ("if no ", "NO"),
                ("if none", "NONE"),
            ]
            _msg_lower = message.lower()
            _check_lower = steps[0].lower()
            for _phrase, _marker in _neg_phrases:
                if _phrase in _msg_lower:
                    # Only fix if the Check: step is missing negation words
                    _neg_words = ["no ", "not ", "don't", "dont", "haven't", "havent", "none"]
                    _check_body = _check_lower[len("check:"):].strip()
                    if not any(w in _check_body for w in _neg_words):
                        # Prepend NO to the check body
                        body = steps[0][len("Check:"):].strip()
                        steps[0] = f"Check: I have NO {body.lstrip('I have ').lstrip('there are ').lstrip('any ')}"
                    break
        if isinstance(steps, list) and steps:
            # Flatten one level: model sometimes returns [[step1, step2]] instead of [step1, step2]
            if len(steps) == 1 and isinstance(steps[0], list):
                steps = steps[0]
            # Ensure all items are strings
            steps = [s for s in steps if isinstance(s, str)]
            if steps:
                return steps[:MAX_STEPS]
    except Exception:
        pass
    return [message]  # fallback: treat as single step


def evaluate_condition(condition_text: str, observed_result: str, router) -> bool:
    """After observing a step's result, ask the LLM whether a stated condition
    was satisfied. Used for conditional steps like 'if unread important emails exist'."""
    prompt = f"""Based on this observed result, answer ONLY "true" or "false" (nothing else).

Condition to check: {condition_text}
Observed result: {observed_result[:1500]}

IMPORTANT — handle negation carefully:
- If the condition contains "no", "none", "don't have", "not have", "zero", evaluate
  whether that NEGATIVE state is true (e.g. "I have NO reminders" is TRUE when the
  result shows an empty list or "no reminders", and FALSE when reminders are listed).
- If the condition is positive (no negation words), evaluate whether the thing EXISTS
  in the result.
- Read the condition EXACTLY as written — do not flip its meaning.

Is the condition true? Answer ONLY "true" or "false"."""
    try:
        raw = router.chat(prompt, task="fast", web_search=False).strip().lower()
        return raw.startswith("true")
    except Exception:
        return False


def run_agentic_loop(message: str, router, memory=None) -> str:
    """Main entry point. Plans steps, executes them via the existing tool
    dispatcher, evaluates conditions, and returns a synthesized final reply."""
    from tools.dispatcher import detect_intent, run_tool

    steps = plan_steps(message, router)
    results = []

    i = 0
    while i < len(steps) and i < MAX_STEPS:
        step = steps[i]

        # Conditional gate: "If true: ..." / "If there are ... : ..." steps
        # get skipped unless the immediately preceding observation satisfied
        # the condition it depends on.
        is_conditional_action = step.lower().startswith(("if true", "if yes", "if there are", "if any"))
        if is_conditional_action and results:
            last_condition_text = steps[i - 1] if i > 0 else ""
            last_result = results[-1]["result"] if results else ""
            condition_met = evaluate_condition(last_condition_text, last_result, router)
            if not condition_met:
                results.append({"step": step, "result": "(skipped — condition not met)"})
                i += 1
                continue

        # Strip conditional prefixes like "If true:" / "If yes:" before
        # intent detection — otherwise the prefix confuses detect_intent
        # and it silently falls through to a chat reply that HALLUCINATES
        # having done the action, instead of actually calling the tool.
        _clean_step = re.sub(
            r'^\s*if\s+(true|yes|there are|any)[:,]?\s*',
            '', step, flags=re.IGNORECASE
        ).strip()

        SAFE_CHECK_ACTIONS = {
            ("gmail", "read"), ("gmail", "search"),
            ("weather", None),
            ("reminder", "list"), ("reminders", "list"),
            ("calendar", "search"), ("calendar", "read"), ("calendar", "list"),
            ("memory_search", "search"),
            ("files", "search"),
        }
        _step_lower = step.strip().lower()
        _lookup_words = (
            "check:", "check ", "is there", "are there", "any emails", "any email",
            "look for", "search for", "find out", "see if", "verify"
        )
        is_check_step = _step_lower.startswith(("check:", "if true: check", "if true:check")) \
            or (_step_lower.startswith("if true:") and any(w in _step_lower for w in _lookup_words))
        try:
            intent = detect_intent(_clean_step)
            if is_check_step and intent["tool"] != "none":
                key_specific = (intent["tool"], intent.get("action"))
                key_generic = (intent["tool"], None)
                if key_specific not in SAFE_CHECK_ACTIONS and key_generic not in SAFE_CHECK_ACTIONS:
                    result = (f"(check step blocked: classifier returned a non-read-only "
                              f"action {intent['tool']}/{intent.get('action')} for a Check: "
                              f"step — refusing to execute for safety)")
                    results.append({"step": step, "result": result})
                    i += 1
                    continue
            if intent["tool"] == "none":
                # Not a tool step — treat as a normal chat/reasoning step
                result = router.chat(_clean_step, task="fast", web_search=False)
            else:
                result = run_tool(intent, _clean_step)
        except Exception as e:
            result = f"(step failed: {e})"

        # WhatsApp send inside the loop needs a real yes/no confirmation —
        # we don't bypass that safety gate. Stop the loop right here, save
        # the pending action so client.py's EXISTING confirmation handler
        # picks it up on the user's next "yes", and return the prompt
        # directly instead of continuing to synthesis.
        if isinstance(result, str) and result.startswith("WHATSAPP_CONFIRM_NEEDED|"):
            _, _wa_contact, _wa_text = result.split("|", 2)
            if memory:
                memory.set_pending_action("whatsapp_send", {"contact": _wa_contact, "text": _wa_text})
            return f'Send "{_wa_text}" to {_wa_contact}? Reply yes or no.'

        results.append({"step": step, "result": result})
        i += 1

    # Synthesize final reply from all step results
    summary_lines = []
    for r in results:
        summary_lines.append(f"[{r['step']}]: {r['result']}")
    combined = "\n\n".join(summary_lines)

    synth_prompt = f"""The user asked: "{message}"

Here are the ACTUAL results of each step taken to fulfill this request:

{combined}

Write a single, natural, concise reply to the user based ONLY on these actual results.
Do NOT claim any action succeeded unless its result explicitly confirms it (e.g. a
tool result containing "sent", "Message sent", a message ID, or similar concrete
confirmation). If a step was skipped or failed, say so plainly. Never say "I've sent"
or "I've done X" unless the result text actually shows that happened."""
    try:
        final = router.chat(synth_prompt, task="fast", web_search=False)
        return final
    except Exception:
        return combined
