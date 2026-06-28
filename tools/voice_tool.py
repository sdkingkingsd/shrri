"""Voice tool — Edge TTS, PallaviNeural Tamil female, +20% rate."""
import subprocess, tempfile, os, re, asyncio
import speech_recognition as sr
VOICE = "ta-IN-PallaviNeural"
VOICE_RATE = "+5%"
async def _speak_async(text: str):
    import edge_tts
    text = text.replace("SHRRI", "Shree").replace("shrri", "Shree")
    # Remove hyphens between English words and Tamil suffixes
    text = re.sub(r'([a-zA-Z0-9])-([அ-ஹா-ௌ])', lambda m: m.group(1) + ' ' + m.group(2), text) if re.search(r'[஀-௿]', text) else text
    # Insert space-comma-space before English words so Pallavi pronounces them
    text = re.sub(r'([a-zA-Z][a-zA-Z0-9]*)', lambda m: ' , ' + m.group(1), text) if re.search(r'[஀-௿]', text) else text
    text = re.sub(r' +', ' ', text).strip()
    text = re.sub(r"[*#`•]", "", text).strip()
    if not text:
        return
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir="/tmp") as f:
        fname = f.name
    communicate = edge_tts.Communicate(text, VOICE, rate=VOICE_RATE)
    await communicate.save(fname)
    subprocess.run(["mpg123", "-q", fname],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        os.unlink(fname)
    except Exception:
        pass
def speak(text: str):
    try:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    pool.submit(asyncio.run, _speak_async(text)).result()
            else:
                loop.run_until_complete(_speak_async(text))
        except RuntimeError:
            asyncio.run(_speak_async(text))
    except Exception:
        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang="ta", slow=False)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir="/tmp") as f:
                fname = f.name
            tts.save(fname)
            subprocess.run(["mpg123", "-q", fname],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.unlink(fname)
        except Exception:
            subprocess.run(["espeak-ng", "-v", "ta", text],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
def listen() -> str:
    import threading
    result = [""]
    def _listen():
        try:
            r = sr.Recognizer()
            r.energy_threshold = 300
            with sr.Microphone(device_index=4) as source:
                print("Shree: Listening...")
                r.adjust_for_ambient_noise(source, duration=1)
                try:
                    audio = r.listen(source, timeout=8, phrase_time_limit=15)
                except sr.WaitTimeoutError:
                    return
            for lang_code in ["ta-IN", "en-IN"]:
                try:
                    result[0] = r.recognize_google(audio, language=lang_code)
                    return
                except sr.UnknownValueError:
                    continue
                except sr.RequestError as e:
                    print(f"Speech error: {e}")
                    return
        except Exception as e:
            print(f"Listen error: {e}")
    t = threading.Thread(target=_listen)
    t.start()
    t.join(timeout=20)
    return result[0]
