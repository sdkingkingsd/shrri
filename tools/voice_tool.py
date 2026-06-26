"""Voice tool — Edge TTS, NeerjaNeural Indian female, pipeline."""
import subprocess, tempfile, os, re, asyncio
import speech_recognition as sr

VOICE = "en-IN-NeerjaNeural"

async def _speak_async(text: str):
    import edge_tts
    text = text.replace("SHRRI", "Shree").replace("shrri", "Shree")
    text = re.sub(r"[*#`•]", "", text).strip()
    if not text:
        return
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir="/tmp") as f:
        fname = f.name
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(fname)
    subprocess.run(["mpg123", "-q", fname],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        os.unlink(fname)
    except Exception:
        pass

def speak(text: str):
    try:
        asyncio.run(_speak_async(text))
    except Exception:
        # Fallback to gTTS
        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang="en", tld="co.in", slow=False)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir="/tmp") as f:
                fname = f.name
            tts.save(fname)
            subprocess.run(["mpg123", "-q", fname],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.unlink(fname)
        except Exception:
            subprocess.run(["espeak-ng", "-v", "en-us", text],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def listen() -> str:
    r = sr.Recognizer()
    try:
        import ctypes
        asound = ctypes.cdll.LoadLibrary("libasound.so")
        asound.snd_lib_error_set_handler(ctypes.CFUNCTYPE(None)(lambda *_: None))
    except Exception:
        pass
    with sr.Microphone() as source:
        print("Shree: Listening...")
        r.adjust_for_ambient_noise(source, duration=1)
        try:
            audio = r.listen(source, timeout=8, phrase_time_limit=15)
        except sr.WaitTimeoutError:
            return ""
    for lang_code in ["ta-IN", "en-IN"]:
        try:
            return r.recognize_google(audio, language=lang_code)
        except sr.UnknownValueError:
            continue
        except sr.RequestError as e:
            print(f"Speech error: {e}")
            return ""
    return ""
