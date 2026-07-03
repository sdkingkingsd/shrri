"""
Recovery Engine — SHRRI Phase 8
If a computer_use action fails or verification says it didn't work,
this engine attempts alternative strategies to achieve the goal.
"""
import time
from tools.computer_use_tool import (
    take_screenshot, keyboard_key, mouse_click,
    keyboard_type, get_active_window, list_windows
)

MAX_RETRIES = 3

def _escape_and_retry(action_fn, *args, **kwargs):
    """Press Escape, wait, then retry the action."""
    keyboard_key("Escape")
    time.sleep(0.5)
    return action_fn(*args, **kwargs)

def _close_dialogs():
    """Try to dismiss common blocking dialogs."""
    keyboard_key("Return")        # confirm dialog
    time.sleep(0.3)
    keyboard_key("Escape")        # cancel dialog
    time.sleep(0.3)

def recover(failed_action: str, original_result: str, context: dict = None) -> str:
    """
    Attempt to recover from a failed computer_use action.
    
    failed_action: human description of what was attempted
    original_result: the GAP/error string returned
    context: optional dict with extra hints (e.g. target_window, coords)
    Returns: result string
    """
    context = context or {}
    errors = []

    for attempt in range(1, MAX_RETRIES + 1):
        # Strategy 1: dismiss dialogs / refocus and retry
        if attempt == 1:
            _close_dialogs()
            active = get_active_window()
            errors.append(f"Attempt {attempt}: cleared dialogs, active window = {active}")

        # Strategy 2: refocus target window if specified
        elif attempt == 2:
            target = context.get("target_window", "")
            if target:
                from tools.computer_use_tool import focus_window
                focus_window(target)
                time.sleep(0.3)
                errors.append(f"Attempt {attempt}: refocused '{target}'")
            else:
                # Try clicking center of screen as a generic refocus
                mouse_click(960, 540)
                time.sleep(0.3)
                errors.append(f"Attempt {attempt}: clicked screen center to refocus")

        # Strategy 3: take a screenshot and report state for manual review
        elif attempt == 3:
            snap = take_screenshot()
            errors.append(f"Attempt {attempt}: screenshot taken for diagnosis — {snap}")
            windows = list_windows()
            return (
                f"GAP: Recovery failed after {MAX_RETRIES} attempts.\n"
                f"Original error: {original_result}\n"
                f"Recovery log:\n" + "\n".join(f"  {e}" for e in errors) + "\n"
                f"Current windows:\n{windows}\n"
                f"Screenshot saved for review."
            )

        # After each recovery attempt, report state
        time.sleep(0.5)

    return f"GAP: recovery exhausted — {'; '.join(errors)}"


def safe_execute(action_fn, description: str, *args, **kwargs) -> str:
    """
    Wraps a computer_use action with automatic verification + recovery.
    
    action_fn: callable from computer_use_tool
    description: human description of what this action should do
    """
    from tools.verification_engine import verify_action

    result = action_fn(*args, **kwargs)

    if result.startswith("GAP"):
        recovery_result = recover(description, result)
        return recovery_result

    # Verify the action worked
    verification = verify_action(description)
    if not verification.get("success", True):
        # Try recovery
        recovery = recover(description, f"Verification failed: {verification.get('observation','')}")
        return f"⚠️ Action ran but verification uncertain.\n{recovery}"

    return result
