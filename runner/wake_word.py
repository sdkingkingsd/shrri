"""
Wake Word Engine — SHRRI AI OS v2

Wraps openWakeWord for CPU-only wake word detection. Runs on a stream
of int16 audio chunks (16kHz) and returns a detection when the score
crosses the threshold.

PLACEHOLDER MODEL: using bundled "hey_jarvis" until a custom "hey_shree"
model is trained via openWakeWord's synthetic-data training pipeline
(needs GPU/Colab — separate task, tracked in BUILD_TRACKER.md).
To swap in the trained model later: replace DEFAULT_MODEL_PATH below
with the path to the new .onnx file. No other code changes needed.
"""

import numpy as np
import openwakeword

# TODO: replace with trained hey_shree.onnx once available
DEFAULT_MODEL_PATH = (
    openwakeword.get_pretrained_model_paths()[2]  # hey_jarvis_v0.1.onnx
)
DEFAULT_THRESHOLD = 0.5


class WakeWordEngine:
    def __init__(self, model_path: str = DEFAULT_MODEL_PATH,
                 threshold: float = DEFAULT_THRESHOLD):
        self.model = openwakeword.Model(wakeword_model_paths=[model_path])
        self.threshold = threshold
        self.model_name = list(self.model.models.keys())[0] if hasattr(self.model, "models") else None

    def process_chunk(self, audio_chunk: np.ndarray) -> dict:
        """
        audio_chunk: int16 numpy array, 16kHz mono, any length
        (openWakeWord internally buffers to its required frame size).
        Returns {"detected": bool, "score": float, "model": str}
        """
        prediction = self.model.predict(audio_chunk)
        model_name, score = next(iter(prediction.items()))
        return {
            "detected": score >= self.threshold,
            "score": float(score),
            "model": model_name,
        }

    def reset(self):
        """Clear internal buffers between listening sessions."""
        self.model.reset()
