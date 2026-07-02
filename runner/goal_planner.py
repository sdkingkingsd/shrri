"""
Goal Planner — SHRRI AI OS v2 (Phase 4)

Turns a raw user goal (natural language) into a WorkflowGraph ready
for the Execution Scheduler. Unlike Model Selection (keyword-based,
Phase 3), planning genuinely requires judgment about how many steps
a goal needs and how they depend on each other — so this asks an
LLM to produce a structured plan, then parses it defensively into
a graph.

Plan format the LLM is asked to produce (JSON):
[
  {"id": "step1", "prompt": "...", "depends_on": []},
  {"id": "step2", "prompt": "...", "depends_on": ["step1"]}
]

Simple goals (single step, no real decomposition needed) are valid
output too — a one-item list with no dependencies. The planner
doesn't force multi-step plans where one step suffices.
"""

import json
import re

from runner.router_adapter import RouterAdapter as ProviderRouter
from runner.workflow_graph import WorkflowGraph, CycleError

_PLANNER_SYSTEM_PROMPT = (
    "You are a planning assistant. Break the user's goal into an ordered "
    "list of concrete steps needed to accomplish it. If the goal is simple "
    "enough to do in one step, return just one step — do not invent "
    "unnecessary steps.\n\n"
    "Respond with ONLY a JSON array, no prose, no markdown code fences. "
    "Each item must have exactly these fields:\n"
    '  "id": a short unique string identifier for this step (e.g. "step1")\n'
    '  "type": one of "research", "code", "browse", "vision", "memory", '
    '"automation", "security", "testing", "documentation", "linux", "android", "github", or '
    '"llm_call" '
    "(default general reasoning/writing/translation with no special "
    "tool). Pick \"research\" for anything needing current/factual web "
    "info, \"code\" for writing/debugging code (NOT running/testing "
    "it), \"browse\" for actually visiting a live webpage, \"vision\" "
    "for analyzing an image, \"memory\" for remembering/saving a fact "
    "or recalling something previously stored, \"automation\" for "
    "setting reminders, scheduling recurring tasks, or listing/"
    "cancelling existing reminders/automations, \"security\" for "
    "checking system health/status, reviewing denied or suspicious "
    "tool-call attempts, or asking what actions are permitted, "
    "\"testing\" for actually EXECUTING/running a piece of code to see "
    "its real output, or running SHRRI's own regression test suite, "
    "\"documentation\" for writing README/docstring/usage-guide style "
    "documentation content (including explaining what a feature, "
    "command, or part of THIS system does), or reading/saving a doc "
    "file, \"linux\" for controlling THIS laptop directly RIGHT NOW "
    "— locking the screen, shutdown/restart (now, delayed, or "
    "cancelled), setting/changing volume, or brightness (use "
    "\"linux\" for these, NOT \"automation\" — \"automation\" is "
    "only for reminders and recurring scheduled tasks, never "
    "immediate one-time system control), \"android\" for controlling "
    "or checking a PAIRED ANDROID PHONE via adb — listing connected "
    "devices, battery status, screenshot, installing/uninstalling an "
    "APK, or listing installed apps, \"github\" for local git status/"
    "diff/commit/push on the SHRRI repo, or listing/creating GitHub "
    "issues and pull requests via gh, and "
    "\"llm_call\" for everything else (writing, translating, "
    "summarizing given text, creative tasks, math, etc).\n"
    '  "prompt": the actual instruction/question for this step, written so '
    "it can be sent to another AI model on its own. If this step needs "
    "the output of an earlier step, reference it with the exact "
    "placeholder syntax {output_of_<id>}, e.g. {output_of_step1} — this "
    "will be automatically replaced with that step's real output.\n"
    '  "depends_on": a list of "id" strings for steps that must complete '
    "before this one can start (empty list if none)\n\n"
    "Example output:\n"
    '[{"id": "step1", "type": "research", "prompt": "Research X", "depends_on": []}, '
    '{"id": "step2", "type": "llm_call", "prompt": "Write a summary of the research", "depends_on": ["step1"]}]'
)


class PlanParseError(Exception):
    pass


def _extract_json_array(text: str) -> str:
    """LLMs sometimes wrap JSON in prose or ```json fences. Pull out
    the first [...] block we can find."""
    fence_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1)
    bracket_match = re.search(r"\[.*\]", text, re.DOTALL)
    if bracket_match:
        return bracket_match.group(0)
    raise PlanParseError(f"No JSON array found in planner output: {text[:200]!r}")


def _repair_truncated_json_array(json_str: str) -> str:
    """Best-effort repair for an array cut off mid-generation: closes
    any dangling string/object/array so json.loads has a chance."""
    s = json_str.rstrip()
    in_string = False
    escape = False
    depth_stack = []
    for ch in s:
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in "[{":
            depth_stack.append(ch)
        elif ch in "]}":
            if depth_stack:
                depth_stack.pop()
    if in_string:
        s += '"'
    # Drop a trailing dangling comma/partial-key fragment if present
    s = re.sub(r",\s*$", "", s)
    for opener in reversed(depth_stack):
        s += "]" if opener == "[" else "}"
    return s


def _parse_plan(raw_text: str) -> list[dict]:
    json_str = _extract_json_array(raw_text)
    try:
        plan = json.loads(json_str)
    except json.JSONDecodeError as e:
        repaired = _repair_truncated_json_array(json_str)
        try:
            plan = json.loads(repaired)
        except json.JSONDecodeError:
            raise PlanParseError(f"Planner output was not valid JSON: {e}")

    if not isinstance(plan, list) or len(plan) == 0:
        raise PlanParseError("Planner output must be a non-empty JSON array")

    for step in plan:
        if not all(k in step for k in ("id", "prompt", "depends_on")):
            raise PlanParseError(f"Step missing required fields: {step}")
        step.setdefault("type", "llm_call")
        if step["type"] not in ("research", "code", "browse", "vision", "memory", "automation", "security", "testing", "documentation", "linux", "android", "github", "llm_call"):
            step["type"] = "llm_call"  # unknown type from LLM -> safe default

    return plan


def plan_to_graph(plan: list[dict]) -> tuple[WorkflowGraph, dict]:
    """
    Builds a WorkflowGraph from a parsed plan. Returns (graph, id_map)
    where id_map maps the planner's string ids (e.g. "step1") to the
    actual task_ids the underlying TaskQueue assigned.
    """
    graph = WorkflowGraph()
    id_map: dict[str, str] = {}

    remaining = {step["id"]: step for step in plan}
    added = set()

    # Add steps in dependency order — repeatedly add any step whose
    # dependencies have already been added, until all are placed or
    # we detect nothing more can be added (broken/unknown reference).
    while remaining:
        progressed = False
        for step_id, step in list(remaining.items()):
            deps = step["depends_on"]
            if all(d in added for d in deps):
                real_deps = [id_map[d] for d in deps]
                # Store step-id -> real task_id for each dependency so the
                # scheduler can substitute {output_of_<step_id>} placeholders
                # in this step's prompt with the actual completed result.
                dep_task_ids = {d: id_map[d] for d in deps}
                task_id = graph.add_task(
                    step.get("type", "llm_call"),
                    {"prompt": step["prompt"], "dep_task_ids": dep_task_ids},
                    depends_on=real_deps,
                )
                id_map[step_id] = task_id
                added.add(step_id)
                del remaining[step_id]
                progressed = True
        if not progressed:
            raise PlanParseError(
                f"Could not resolve dependencies for steps: {list(remaining.keys())} "
                f"(unknown or circular references)"
            )

    return graph, id_map


def plan_goal(goal: str, provider_router: ProviderRouter | None = None, verbose: bool = False) -> tuple[WorkflowGraph, dict]:
    """
    Full pipeline: raw goal -> LLM plan -> parsed -> WorkflowGraph.
    Raises PlanParseError or CycleError on bad output.
    """
    router = provider_router or ProviderRouter(web_search=False)
    full_prompt = f"{_PLANNER_SYSTEM_PROMPT}\n\nUser goal: {goal}"
    result = router.generate(full_prompt)

    if not result["success"]:
        raise RuntimeError(f"Planner LLM call failed: {result.get('error')}")

    if verbose:
        print(f"[goal_planner] Raw planner output: {result['text']!r}")

    plan = _parse_plan(result["text"])

    if verbose:
        print(f"[goal_planner] Parsed plan with {len(plan)} step(s)")

    return plan_to_graph(plan)
