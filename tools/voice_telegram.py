"""Voice handling for Telegram - receive voice notes (STT) and send voice replies (TTS)."""
import os
import subprocess
import tempfile

def transcribe_ogg(ogg_path: str) -> str:
    """Convert a Telegram .ogg voice note to text using local Whisper."""
    wav_path = ogg_path.rsplit(".", 1)[0] + ".wav"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", ogg_path, "-ar", "16000", "-ac", "1", wav_path],
            capture_output=True, timeout=30, check=True
        )
        from tools.voice_input import _get_model
        model = _get_model()
        segments, _ = model.transcribe(wav_path, language="en")
        text = " ".join([seg.text.strip() for seg in segments])
        return text.strip()
    finally:
        for p in (wav_path,):
            try:
                os.remove(p)
            except Exception:
                pass

def text_to_voice_ogg(text: str) -> str:
    """Generate a Telegram-compatible .ogg voice reply from text. Returns the file path."""
    import edge_tts
    import asyncio
    import re

    clean_text = re.sub(r"[*#`•]", "", text).strip()
    clean_text = clean_text.replace("SHRRI", "Shree").replace("shrri", "Shree")
    if not clean_text:
        return None

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir="/tmp") as f:
        mp3_path = f.name
    ogg_path = mp3_path.rsplit(".", 1)[0] + ".ogg"

    async def _gen():
        communicate = edge_tts.Communicate(clean_text, "ta-IN-PallaviNeural", rate="+5%")
        await communicate.save(mp3_path)

    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_gen())
        loop.close()
    except Exception:
        return None

    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", mp3_path, "-c:a", "libopus", ogg_path],
            capture_output=True, timeout=30, check=True
        )
    finally:
        try:
            os.remove(mp3_path)
        except Exception:
            pass

    return ogg_path if os.path.exists(ogg_path) else None
