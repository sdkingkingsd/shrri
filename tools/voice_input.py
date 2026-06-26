import sounddevice as sd
import numpy as np
import tempfile
import wave
from faster_whisper import WhisperModel

# Loads once, reused across calls — "base" is a good speed/accuracy balance for English
_model = None

def _get_model():
    global _model
    if _model is None:
        print("[Voice] Loading speech recognition model (first time only)...")
        _model = WhisperModel("base", device="cpu", compute_type="int8")
    return _model


def record_audio(samplerate=16000):
    """Push-to-talk: press Enter to start, press Enter again to stop."""
    print("\n🎙️  Press Enter to START recording...")
    input()
    print("🔴 Recording... Press Enter to STOP.")

    frames = []
    stream = sd.InputStream(samplerate=samplerate, channels=1, dtype="int16")
    stream.start()

    import threading
    stop_flag = {"stop": False}

    def wait_for_enter():
        input()
        stop_flag["stop"] = True

    t = threading.Thread(target=wait_for_enter)
    t.start()

    while not stop_flag["stop"]:
        data, _ = stream.read(1024)
        frames.append(data.copy())

    stream.stop()
    stream.close()
    t.join()

    audio = np.concatenate(frames, axis=0)
    return audio, samplerate


def transcribe(audio, samplerate=16000) -> str:
    """Save audio to temp WAV, transcribe with Whisper, return text."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(samplerate)
            wf.writeframes(audio.tobytes())

        model = _get_model()
        segments, _ = model.transcribe(tmp.name, language="en")
        text = " ".join([seg.text.strip() for seg in segments])
        return text.strip()


def listen() -> str:
    """Full flow: record then transcribe. Returns the recognized text."""
    audio, sr = record_audio()
    print("🧠 Transcribing...")
    text = transcribe(audio, sr)
    print(f"📝 You said: {text}")
    return text


if __name__ == "__main__":
    print("Testing voice input...")
    result = listen()
    print(f"\nFinal result: {result}")
