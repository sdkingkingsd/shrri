"""
Deterministic math and date arithmetic for SHRRI.

Why this exists: direct testing (thinking_test.py, plus the birthday-puzzle
loop) proved the LLM cannot reliably do multi-step arithmetic or date math —
it invents plausible-looking wrong numbers, or worse, gets stuck in a
self-contradiction loop trying to "verify" bad arithmetic. This tool routes
those calculations to real Python instead, so the answer is always correct
and the model never has to guess a number.
"""
import re
from datetime import datetime, timedelta

import ast
import operator


# --- Safe arithmetic evaluator (NOT eval() — no arbitrary code execution) ---

_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Only numbers are allowed")
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPS:
            raise ValueError(f"Operator {op_type} not allowed")
        return _ALLOWED_OPS[op_type](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPS:
            raise ValueError(f"Operator {op_type} not allowed")
        return _ALLOWED_OPS[op_type](_safe_eval(node.operand))
    raise ValueError(f"Unsupported expression: {ast.dump(node)}")


def safe_calculate(expression: str) -> str:
    """Evaluate a basic arithmetic expression safely (+ - * / ^ % and parens).
    Caret (^) is treated as power, matching how people type it casually."""
    cleaned = expression.strip().replace("^", "**").replace("x", "*").replace("X", "*")
    # Strip anything that isn't a digit, operator, paren, dot, or space
    cleaned = re.sub(r"[^0-9+\-*/().% ]", "", cleaned)
    if not cleaned.strip():
        return "GAP: no valid arithmetic expression found"
    try:
        tree = ast.parse(cleaned, mode="eval")
        result = _safe_eval(tree.body)
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return f"🧮 {expression.strip()} = {result}"
    except ZeroDivisionError:
        return "GAP: division by zero in expression"
    except Exception as e:
        return f"GAP: could not safely evaluate expression — {e}"


def extract_and_calculate(message: str) -> str:
    """Pull an arithmetic expression out of a natural-language message and
    compute it. Handles things like '17 times 23', '17 * 23', 'what is 5 + 9'."""
    msg = message.lower()
    msg = msg.replace("times", "*").replace("multiplied by", "*")
    msg = msg.replace("plus", "+").replace("added to", "+")
    msg = msg.replace("minus", "-").replace("subtracted from", "-")
    msg = msg.replace("divided by", "/").replace("over", "/")
    msg = msg.replace("to the power of", "**").replace("squared", "**2")

    match = re.search(r"[-+]?\d+(\.\d+)?\s*(?:[\+\-\*/%\^]|\*\*)\s*[-+]?\d+(\.\d+)?(?:\s*(?:[\+\-\*/%\^]|\*\*)\s*[-+]?\d+(\.\d+)?)*", msg)
    if not match:
        return "GAP: no arithmetic expression found in message"
    return safe_calculate(match.group(0))


# --- Date arithmetic ---

_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_WEEKDAY_LOOKUP = {name.lower(): i for i, name in enumerate(_WEEKDAYS)}


def add_days(base_date: datetime, days: int) -> datetime:
    return base_date + timedelta(days=days)


def describe_date(d: datetime) -> str:
    return d.strftime("%A, %B %d, %Y")


def relative_date_calc(message: str, reference_date: datetime = None) -> str:
    """Handle simple relative date phrasing: 'N days after/before <date or
    relative point>'. Reference date defaults to now. This deliberately
    handles only simple, single-step relative offsets — for anything more
    nested/ambiguous, it returns a GAP so the LLM doesn't have to guess
    silently and so we know to extend this function rather than trust a
    hallucinated date."""
    ref = reference_date or datetime.now()
    msg = message.lower()

    m = re.search(r"(\d+)\s+days?\s+(after|before|from)\s+(today|now|yesterday|tomorrow)", msg)
    if m:
        n = int(m.group(1))
        direction = m.group(2)
        anchor_word = m.group(3)
        anchor = ref
        if anchor_word == "yesterday":
            anchor = ref - timedelta(days=1)
        elif anchor_word == "tomorrow":
            anchor = ref + timedelta(days=1)
        offset = n if direction in ("after", "from", "from today") else -n
        result = add_days(anchor, offset)
        return f"📅 {describe_date(result)} ({result.strftime('%Y-%m-%d')})"

    return "GAP: date expression too complex for deterministic date_tool — needs manual step-through"
