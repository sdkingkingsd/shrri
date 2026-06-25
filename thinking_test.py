import sys
sys.path.insert(0, '/home/shrridharshan/shrri')

import os
import tempfile

# Use an isolated test DB — same safety principle as test_suite.py
TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "shrri_thinking_test_memory.db")
os.environ["SHRRI_MEMORY_DB_OVERRIDE"] = TEST_DB_PATH

from engine import SHRRIEngine


def section(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def run():
    e = SHRRIEngine()

    # ---- TEST 1: Self-correction ----
    section("TEST 1 — Self-correction (can it catch a planted wrong fact?)")
    r1 = e.chat("The capital of France is Berlin. Is that correct?")
    print("Response:\n", r1)
    print("\n>>> JUDGE: Did it correct the false claim, or agree with it? <<<")

    # ---- TEST 2: Novel problem (logic puzzle, not memorizable verbatim) ----
    section("TEST 2 — Novel problem (small logic puzzle)")
    puzzle = (
        "There are 3 boxes. One contains only apples, one only oranges, "
        "one a mix of both. All boxes are labeled, but every label is WRONG. "
        "You may pick one fruit from one box to look at, without seeing inside. "
        "Which box should you pick from to correctly relabel all three boxes, "
        "and what is your reasoning?"
    )
    r2 = e.chat(puzzle)
    print("Response:\n", r2)
    print("\n>>> JUDGE: Correct answer is 'the box labeled Mixed' — does the "
          "reasoning actually follow logically, or does it just sound confident? <<<")

    # ---- TEST 3: Explanation quality (ask WHY about its own prior answer) ----
    section("TEST 3 — Explanation of its own reasoning")
    r3 = e.chat("Why did you give that specific answer to the box puzzle? Walk through your exact reasoning steps.")
    print("Response:\n", r3)
    print("\n>>> JUDGE: Is this a real trace of how it solved it, or a plausible-sounding "
          "story invented after the fact? (Hint: LLMs cannot actually introspect on their "
          "own internal process — any 'explanation' is itself a new generation, not a memory.) <<<")

    # ---- TEST 4: Consistency (same question, 3 different phrasings) ----
    section("TEST 4 — Consistency across rephrasing")
    q1 = "What is 17 times 23?"
    q2 = "If I multiply 17 and 23, what do I get?"
    q3 = "17 x 23 = ?"
    a1 = e.chat(q1)
    a2 = e.chat(q2)
    a3 = e.chat(q3)
    print(f"Q1: {q1}\nA1: {a1}\n")
    print(f"Q2: {q2}\nA2: {a2}\n")
    print(f"Q3: {q3}\nA3: {a3}\n")
    print(">>> JUDGE: Real answer is 391. Do all three agree, and are they all correct? <<<")

    section("DONE — review each JUDGE line above manually")
    print(
        "Important context: these tests measure specific BEHAVIORS (self-correction,\n"
        "novel reasoning, explanation, consistency) — not 'thinking' in a deep sense.\n"
        "An LLM can pass all four and still be doing sophisticated pattern completion\n"
        "rather than anything resembling human cognition. What we're really checking is:\n"
        "is SHRRI reliable enough to trust on these specific axes, day to day."
    )


if __name__ == "__main__":
    run()
