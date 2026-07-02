"""
Conversation Controller — SHRRI AI OS v2

Orchestrates the voice input pipeline: wake word detection -> audio
capture -> STT transcription -> language detection -> handoff to Runner.

This module does NOT touch the microphone directly — it expects audio
chunks to be fed in (from pyaudio or similar) and manages the state
machine between "idle / listening for wake word" and "actively
capturing a command after wake word fired".

State machine:
  IDLE -> (wake word detected) -> LISTENING -> (silence/timeout) ->
  TRANSCRIBING -> (text ready) -> back to IDLE, text handed to caller
"""

import time
import numpy as np
from pathlib import Path
from runner.wake_word import WakeWordEngine
from runner.speech_to_text import SpeechToText
from runner.language_detection import LanguageDetectionEngine

STATE_IDLE = "idle"
STATE_LISTENING = "listening"
STATE_TRANSCRIBING = "transcribing"

LISTEN_TIMEOUT_SECONDS = 8  # max time to capture a command after wake word


class ConversationController:
    def __init__(self, on_command_ready=None):
        """
        on_command_ready: callback(text: str, language_info: dict) -> None
        Called once a full command has been captured and transcribed.
        """
        self.wake_word = WakeWordEngine()
        self.stt = SpeechToText()
        self.lang_detect = LanguageDetectionEngine()
        self.on_command_ready = on_command_ready

        self.state = STATE_IDLE
        self._listen_started_at = None
        self._captured_chunks = []

    def feed_audio_chunk(self, chunk: np.ndarray):
        """
        Feed one chunk of int16 16kHz mono audio. Called continuously
        from the mic capture loop. Drives the internal state machine.
        """
        if self.state == STATE_IDLE:
            result = self.wake_word.process_chunk(chunk)
            if result["detected"]:
                self._enter_listening()

        elif self.state == STATE_LISTENING:
            self._captured_chunks.append(chunk)
            elapsed = time.time() - self._listen_started_at
            if elapsed >= LISTEN_TIMEOUT_SECONDS:
                self._finish_capture()

    def _enter_listening(self):
        self.state = STATE_LISTENING
        self._listen_started_at = time.time()
        self._captured_chunks = []

    def _finish_capture(self):
        self.state = STATE_TRANSCRIBING
        audio = np.concatenate(self._captured_chunks) if self._captured_chunks else np.array([], dtype=np.int16)

        # write to a temp wav for whisper-cli (file-based interface)
        tmp_path = Path("/tmp/shrri_capture.wav")
        self._write_wav(tmp_path, audio)

        result = self.stt.transcribe(str(tmp_path))
        text = result["text"] if result["success"] else ""

        if text and self.on_command_ready:
            lang_info = self.lang_detect.detect(text)
            self.on_command_ready(text, lang_info)

        self.wake_word.reset()
        self.state = STATE_IDLE

    def _write_wav(self, path: Path, audio: np.ndarray, sample_rate: int = 16000):
        import wave
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # int16
            wf.setframerate(sample_rate)
            wf.writeframes(audio.tobytes())
