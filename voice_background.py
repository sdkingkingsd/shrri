"""
voice_background.py - Always-on background voice assistant for SHRRI.

Continuously listens to the microphone in short rolling chunks using a
fast/lightweight Whisper "tiny" model just to detect the wake word
("shrri" / close variants). Once detected, records the actual command,
transcribes it with the more accurate "base" model, runs it through
SHRRI's engine, speaks the reply out loud through the speakers, and
logs the text exchange to Telegram.

Run as a standalone systemd service, separate from the Telegram bot.
"""
import os
import sys
import time
import tempfile
import wave
import numpy as np
import sounddevice as sd

sys.path.insert(0, os.path.expanduser("~/shrri"))

SAMPLE_RATE = 16000
CHUNK_SECONDS = 3          # rolling window length for wake-word check
COMMAND_SECONDS = 6        # how long to record after wake word triggers
WAKE_WORDS = ["shrri", "shree", "shri", "siri shri", "hey shrri", "hey shree"]

_tiny_model = None
_base_model = None


def _get_tiny_model():
    global _tiny_model
    if _tiny_model is None:
        from faster_whisper import WhisperModel
        print("[voice_bg] Loading tiny model for wake-word detection...")
        _tiny_model = WhisperModel("tiny", device="cpu", compute_type="int8")
    return _tiny_model


def _get_base_model():
    global _base_model
    if _base_model is None:
        from tools.voice_input import _get_model
        _base_model = _get_model()
    return _base_model


def _record(seconds: float) -> np.ndarray:
    audio = sd.rec(int(seconds * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                    channels=1, dtype="int16")
    sd.wait()
    return audio


def _save_wav(audio: np.ndarray) -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir="/tmp") as f:
        path = f.name
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())
    return path


def _contains_wake_word(text: str) -> bool:
    t = text.lower()
    return any(w in t for w in WAKE_WORDS)


def _send_telegram_log(user_text: str, reply_text: str):
    try:
        from shrri_config import BOT_TOKEN, YOUR_ID
        import urllib.request
        import urllib.parse
        msg = "Voice: " + user_text + "\nReply: " + reply_text
        url = "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage"
        data = urllib.parse.urlencode({"chat_id": YOUR_ID, "text": msg[:4000]}).encode()
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print("[voice_bg] Telegram log failed:", e)


def main():
    print("[voice_bg] Starting background voice listener. Say SHRRI to wake it.")
    _get_tiny_model()

    while True:
        try:
            chunk = _record(CHUNK_SECONDS)
            wav_path = _save_wav(chunk)
            model = _get_tiny_model()
            segments, _ = model.transcribe(wav_path, language="en", vad_filter=True)
            text = " ".join([seg.text.strip() for seg in segments]).strip()
            os.remove(wav_path)

            if text and _contains_wake_word(text):
                print("[voice_bg] Wake word detected:", text)
                from tools.voice_tool import speak
                speak("Yes da")

                cmd_audio = _record(COMMAND_SECONDS)
                cmd_wav = _save_wav(cmd_audio)
                base_model = _get_base_model()
                segs, _ = base_model.transcribe(cmd_wav, language="en")
                command_text = " ".join([s.text.strip() for s in segs]).strip()
                os.remove(cmd_wav)

                if not command_text:
                    speak("I did not catch that da")
                    continue

                print("[voice_bg] Command:", command_text)

                from engine import SHRRIEngine
                global _engine
                try:
                    _engine
                except NameError:
                    _engine = SHRRIEngine()

                response = _engine.chat(command_text)
                response_text = response if isinstance(response, str) else str(response)

                speak(response_text)
                _send_telegram_log(command_text, response_text)

        except KeyboardInterrupt:
            print("[voice_bg] Stopped.")
            break
        except Exception as e:
            print("[voice_bg] Error in loop:", e)
            time.sleep(2)


if __name__ == "__main__":
    main()
