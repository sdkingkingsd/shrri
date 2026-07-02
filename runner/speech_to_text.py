"""
Speech To Text — SHRRI AI OS v2

Thin wrapper around the whisper.cpp binary (built separately at
~/whisper.cpp). Shells out to whisper-cli rather than using a Python
binding — keeps the C++ build and Python code decoupled, and lets you
upgrade whisper.cpp independently without touching this file.

Expects: ~/whisper.cpp/build/bin/whisper-cli and a downloaded model
(default: multilingual 'base' model for Tamil/Tanglish support).
"""

import subprocess
import re
from pathlib import Path

WHISPER_BIN = Path.home() / "whisper.cpp" / "build" / "bin" / "whisper-cli"
WHISPER_MODEL = Path.home() / "whisper.cpp" / "models" / "ggml-base.bin"


class SpeechToText:
    def __init__(self, binary: Path = WHISPER_BIN, model: Path = WHISPER_MODEL):
        self.binary = binary
        self.model = model
        if not self.binary.exists():
            raise FileNotFoundError(f"whisper-cli not found at {self.binary}")
        if not self.model.exists():
            raise FileNotFoundError(f"whisper model not found at {self.model}")

    def transcribe(self, audio_path: str, language: str = "auto") -> dict:
        result = subprocess.run(
            [
                str(self.binary),
                "-m", str(self.model),
                "-f", audio_path,
                "-l", language,
                "-nt",  # no timestamps in output text
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            return {"success": False, "text": "", "error": result.stderr.strip()}

        # whisper-cli prints logs to stdout too; the transcription is the
        # last non-empty, non-log line(s). Strip known log prefixes.
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        text_lines = [l for l in lines if not re.match(r"^(whisper_|main:|system_info)", l)]
        text = " ".join(text_lines).strip()

        return {"success": True, "text": text, "error": None}
