"""
voice_live.py - Continuous voice conversation mode (no wake word).
Uses real-time silence detection (webrtcvad) instead of a fixed recording
window, so it reacts as soon as you stop talking - feels more like a
real conversation. Toggled on/off via Telegram /voicemode command.
"""
import os
import sys
import time
import tempfile
import wave
import collections
import numpy as np
import sounddevice as sd
import webrtcvad

sys.path.insert(0, os.path.expanduser("~/shrri"))

SAMPLE_RATE = 16000
FRAME_MS = 30                     # webrtcvad requires 10/20/30 ms frames
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_MS / 1000)
VAD_AGGRESSIVENESS = 2            # 0-3, higher = more aggressive about filtering non-speech
SILENCE_MS_TO_STOP = 800          # how much trailing silence ends the turn
MAX_RECORD_SECONDS = 15           # safety cap so it never records forever
MIN_SPEECH_MS = 300               # ignore turns shorter than this (likely noise blips)
MIN_TEXT_LEN = 3

MIN_AVG_LOGPROB = -1.0
MAX_NO_SPEECH_PROB = 0.6

vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)


def _save_wav(frames: list) -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir="/tmp") as f:
        path = f.name
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))
    return path


def _record_until_silence():
    """Listen continuously, return audio frames once you stop talking (or None if nothing said)."""
    silence_needed = int(SILENCE_MS_TO_STOP / FRAME_MS)
    max_frames = int(MAX_RECORD_SECONDS * 1000 / FRAME_MS)
    min_speech_frames = int(MIN_SPEECH_MS / FRAME_MS)

    ring = collections.deque(maxlen=silence_needed)
    triggered = False
    voiced_frames = []
    speech_frame_count = 0
    total_frames = 0

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                         blocksize=FRAME_SAMPLES) as stream:
        while total_frames < max_frames:
            data, _ = stream.read(FRAME_SAMPLES)
            frame_bytes = data.tobytes()
            total_frames += 1

            is_speech = vad.is_speech(frame_bytes, SAMPLE_RATE)

            if not triggered:
                ring.append((frame_bytes, is_speech))
                if is_speech:
                    speech_frame_count += 1
                    triggered = True
                    voiced_frames.extend([f for f, s in ring])
                    ring.clear()
            else:
                voiced_frames.append(frame_bytes)
                if is_speech:
                    speech_frame_count += 1
                    ring.clear()
                else:
                    ring.append((frame_bytes, is_speech))
                    if len(ring) >= silence_needed and all(not s for _, s in ring):
                        break

    if not triggered or speech_frame_count < min_speech_frames:
        return None
    return voiced_frames


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
        print("[voice_live] Telegram log failed:", e)


def _transcribe_clean(model, wav_path: str) -> str:
    segments, _ = model.transcribe(
        wav_path,
        language="en",
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )
    good_parts = []
    for seg in segments:
        avg_logprob = getattr(seg, "avg_logprob", 0.0)
        no_speech_prob = getattr(seg, "no_speech_prob", 0.0)
        if avg_logprob < MIN_AVG_LOGPROB:
            continue
        if no_speech_prob > MAX_NO_SPEECH_PROB:
            continue
        good_parts.append(seg.text.strip())
    return " ".join(good_parts).strip()


def main():
    print("[voice_live] Voice mode ON. Listening continuously (smart silence detection)...")
    from tools.voice_input import _get_model
    model = _get_model()

    from engine import SHRRIEngine
    engine = SHRRIEngine()

    from tools.voice_tool import speak

    while True:
        try:
            frames = _record_until_silence()
            if not frames:
                continue

            wav_path = _save_wav(frames)
            text = _transcribe_clean(model, wav_path)
            os.remove(wav_path)

            if len(text) < MIN_TEXT_LEN:
                continue

            print("[voice_live] Heard:", text)
            t0 = time.time()
            response = engine.chat(text)
            t1 = time.time()
            response_text = response if isinstance(response, str) else str(response)
            print("[voice_live] Engine took %.2fs" % (t1 - t0))

            speak(response_text)
            t2 = time.time()
            print("[voice_live] TTS+speak took %.2fs" % (t2 - t1))

            _send_telegram_log(text, response_text)

        except KeyboardInterrupt:
            print("[voice_live] Stopped.")
            break
        except Exception as e:
            print("[voice_live] Error:", e)
            time.sleep(1)


if __name__ == "__main__":
    main()
