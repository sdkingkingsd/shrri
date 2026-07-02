"""
Vision Agent — SHRRI AI OS v2 (Phase 5)

Gives SHRRI the ability to actually look at images, not just text.
Reads a local image file, base64-encodes it, and asks a vision-
capable model what's in it / to answer a question about it.

Tries providers in order (mirrors the "vision" capability list in
capability_map.py) and fails over if one is unavailable/rate-limited
— consistent with the failover behavior everywhere else in this
project. Currently supports:
  - google / gemini-2.5-flash        (via GoogleProvider.chat_with_image)
  - nvidia / meta/llama-3.2-11b-vision-instruct (via NvidiaProvider.chat_with_image)

Payload shape:
  {"prompt": "What's in this image?", "image_path": "/path/to/file.png"}
"""

import base64
import mimetypes

from engine.key_manager import KeyManager
from engine.providers import GoogleProvider, NvidiaProvider

_VISION_CANDIDATES = [
    ("google", "gemini-2.5-flash"),
    ("nvidia", "meta/llama-3.2-11b-vision-instruct"),
]


def _load_image_base64(image_path: str) -> tuple[str, str]:
    """Returns (base64_data, mime_type)."""
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type or not mime_type.startswith("image/"):
        mime_type = "image/jpeg"
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return data, mime_type


class VisionAgent:
    def __init__(self, verbose: bool = False):
        self.km = KeyManager()
        self.verbose = verbose

    def _get_provider_instance(self, provider_name: str):
        if provider_name == "google":
            api_key, _ = self.km.get_best_key("google")
            return GoogleProvider(api_key)
        if provider_name == "nvidia":
            api_key, _ = self.km.get_best_key("nvidia")
            base_url = self.km.get_base_url("nvidia")
            return NvidiaProvider(api_key, base_url)
        raise ValueError(f"No vision support wired up for provider '{provider_name}'")

    def run(self, payload: dict) -> str:
        prompt = payload.get("prompt", "What is in this image?")
        image_path = payload.get("image_path")

        if not image_path:
            raise RuntimeError("Vision agent requires 'image_path' in payload")

        if self.verbose:
            print(f"[vision_agent] Looking at {image_path!r} | prompt: {prompt[:80]!r}")

        image_base64, mime_type = _load_image_base64(image_path)

        last_error = None
        for provider_name, model in _VISION_CANDIDATES:
            try:
                if self.verbose:
                    print(f"[vision_agent] Trying {provider_name} / {model}")
                provider = self._get_provider_instance(provider_name)
                result = provider.chat_with_image(prompt, model, image_base64, mime_type=mime_type)
                if result and result.strip():
                    return result
            except Exception as e:
                last_error = e
                if self.verbose:
                    print(f"[vision_agent] {provider_name} failed: {e}")
                continue

        raise RuntimeError(f"Vision agent: all providers failed. Last error: {last_error}")
