"""
Verification Engine — SHRRI Phase 8
After a computer_use action, verify the result by taking a screenshot
and asking the vision model whether the intended outcome happened.
Uses Router's key rotation + falls back to flash-lite on quota errors.
"""
import os, base64, json, re
from tools.computer_use_tool import take_screenshot

_VISION_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"]

def verify_action(intent_description: str, screenshot_path: str = None) -> dict:
    if not screenshot_path:
        screenshot_path = os.path.expanduser("~/shrri_verify.png")

    snap_result = take_screenshot(screenshot_path)
    if "GAP" in snap_result:
        return {"success": False, "confidence": "low", "observation": snap_result}

    try:
        with open(screenshot_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        from engine.key_manager import KeyManager
        from engine.providers import GoogleProvider

        km = KeyManager()
        prompt = (
            f"I just performed this action on a desktop: \"{intent_description}\"\n\n"
            "Look at this screenshot and tell me:\n"
            "1. Did the action succeed? (yes/no/unclear)\n"
            "2. What do you observe on screen?\n"
            "3. Confidence: high/medium/low\n\n"
            "Reply ONLY as JSON: "
            "{\"success\": true, \"confidence\": \"high\", \"observation\": \"...\"}"
        )

        last_err = None
        for model in _VISION_MODELS:
            try:
                api_key, _ = km.get_best_key("google")
                provider = GoogleProvider(api_key)
                raw = provider.chat_with_image(
                    message=prompt,
                    model=model,
                    image_base64=img_b64,
                    mime_type="image/png"
                )
                clean = re.sub(r"```json|```", "", raw).strip()
                return json.loads(clean)
            except Exception as e:
                last_err = e
                if "429" not in str(e) and "RESOURCE_EXHAUSTED" not in str(e):
                    break  # non-quota error, don't retry other models
                continue   # quota error, try next model

        return {"success": False, "confidence": "low", "observation": f"Verify error: {last_err}"}

    except Exception as e:
        return {"success": False, "confidence": "low", "observation": f"Verify error: {e}"}


def verify_and_report(intent_description: str) -> str:
    v = verify_action(intent_description)
    status = "✅ Verified" if v.get("success") else "⚠️ Uncertain"
    conf = v.get("confidence", "?")
    obs = v.get("observation", "")
    return f"{status} [{conf} confidence]: {obs}"
