"""
Model Selection — SHRRI AI OS v2

Infers the best capability (and therefore model list) for a raw
prompt when the caller doesn't specify one explicitly. This sits
above routing/ranking/failover — it only decides WHICH capability's
candidate list to hand to route(), it does not touch provider order
within that list (Provider Ranking + Offline First already own that).

Keyword-based classifier: fast, deterministic, no extra API call
needed just to pick a capability. Falls back to "conversation" when
nothing matches — matches the existing default behavior exactly.
"""

import re

# Ordered by specificity — more specific capabilities are checked
# first so a prompt like "debug this translation function" matches
# "debugging" before the more generic "translate" keyword fires.
_CAPABILITY_KEYWORDS = {
    "debugging": [
        r"\bdebug\b", r"\bfix this (bug|error|crash)\b", r"\btraceback\b",
        r"\bstack trace\b", r"\bexception\b", r"why (is|does) .* (fail|crash|break)",
    ],
    "coding": [
        r"\bwrite (a |an |some )?(function|script|code|program|class)\b",
        r"\bimplement\b", r"\brefactor\b", r"\bpython\b", r"\bjavascript\b",
        r"```", r"\bfunction\b.*\breturn\b",
    ],
    "math": [
        r"\bsolve\b.*\bequation\b", r"\bcalculate\b", r"\bderivative\b",
        r"\bintegral\b", r"\bmatrix\b", r"\bprobability\b", r"\bsummation\b",
    ],
    "finance": [
        r"\bstock\b", r"\bportfolio\b", r"\binvestment\b", r"\bROI\b",
        r"\bbalance sheet\b", r"\brevenue\b", r"\btaxes?\b", r"\bbudget\b",
    ],
    "medical": [
        r"\bsymptoms?\b", r"\bdiagnos(is|e)\b", r"\bmedication\b",
        r"\bdosage\b", r"\btreatment\b", r"\bdisease\b",
    ],
    "translate": [
        r"\btranslate\b", r"\btranslation\b", r"\bin (french|spanish|german|hindi|tamil|japanese|chinese)\b",
    ],
    "tamil": [
        r"[\u0B80-\u0BFF]",  # Tamil unicode block — actual Tamil script present
    ],
    "summarize": [
        r"\bsummariz(e|ation)\b", r"\bsumma(r|ris)e\b", r"\btl;?dr\b",
        r"\bshorten this\b", r"\bkey points\b",
    ],
    "writing": [
        r"\bwrite (a |an )?(\w+\s)?(essay|article|blog|story|poem|email|letter)\b",
        r"\bdraft\b", r"\bproofread\b", r"\brewrite\b",
    ],
    "ocr": [
        r"\bextract text\b", r"\bread (this|the) (image|photo|scan)\b", r"\bocr\b",
    ],
    "vision": [
        r"\bwhat('s| is) in this image\b", r"\bdescribe (this|the) (image|photo|picture)\b",
        r"\banalyze (this|the) image\b",
    ],
    "document": [
        r"\bthis (pdf|document|docx)\b", r"\bsummarize the document\b",
        r"\bextract .* from (this|the) (pdf|document)\b",
    ],
    "tool_calling": [
        r"\bcall the \w+ (api|function|tool)\b", r"\binvoke\b.*\btool\b",
    ],
    "embeddings": [
        r"\bembedding\b", r"\bvector (search|similarity)\b", r"\bsemantic search\b",
    ],
    "reasoning": [
        r"\bstep by step\b", r"\bwhy\b.*\bhappen\b", r"\bexplain the logic\b",
        r"\bwhat would happen if\b", r"\bprove that\b",
    ],
}

# Compile once at import time.
_COMPILED = {
    cap: [re.compile(pat, re.IGNORECASE) for pat in pats]
    for cap, pats in _CAPABILITY_KEYWORDS.items()
}


def classify(prompt: str) -> str:
    """
    Infer the best capability for a raw prompt. Checks capabilities
    in priority order (most specific first) and returns the first
    match. Falls back to "conversation" — the existing default —
    when nothing matches, so behavior for generic prompts is
    unchanged from before Model Selection existed.
    """
    if not prompt or not prompt.strip():
        return "conversation"

    for cap, patterns in _COMPILED.items():
        for pattern in patterns:
            if pattern.search(prompt):
                return cap

    return "conversation"
