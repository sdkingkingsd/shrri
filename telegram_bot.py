import os, sys, asyncio, logging
sys.path.insert(0, os.path.expanduser("~/shrri"))
from shrri_config import BOT_TOKEN, YOUR_ID


from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from engine import SHRRIEngine

engine = SHRRIEngine()
logging.basicConfig(level=logging.WARNING)

VOICE_PID_FILE = "/tmp/shrri_voice_live.pid"

def _voicemode_status():
    if not os.path.exists(VOICE_PID_FILE):
        return False
    try:
        with open(VOICE_PID_FILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return True
    except Exception:
        return False

async def handle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # Security — only respond to you
    if update.effective_user.id != YOUR_ID:
        return

    raw_text = (update.message.text or "").strip().lower()
    if raw_text in ("/voicemode on", "voice mode on", "voicemode on"):
        if _voicemode_status():
            await update.message.reply_text("Voice mode already on, da.")
        else:
            import subprocess
            proc = subprocess.Popen(
                ["python3", os.path.expanduser("~/shrri/voice_live.py")],
                stdout=open("/tmp/shrri_voice_live.log", "a"),
                stderr=subprocess.STDOUT,
                cwd=os.path.expanduser("~/shrri"),
            )
            with open(VOICE_PID_FILE, "w") as f:
                f.write(str(proc.pid))
            await update.message.reply_text("Voice mode ON da — listening continuously now.")
        return

    if raw_text in ("/voicemode off", "voice mode off", "voicemode off"):
        if not _voicemode_status():
            await update.message.reply_text("Voice mode already off, da.")
        else:
            try:
                with open(VOICE_PID_FILE) as f:
                    pid = int(f.read().strip())
                os.kill(pid, 9)
                os.remove(VOICE_PID_FILE)
                await update.message.reply_text("Voice mode OFF da.")
            except Exception as e:
                await update.message.reply_text("Couldnt stop it cleanly: " + str(e))
        return


    is_voice_input = False
    user_msg = update.message.text or ""

    if not user_msg and update.message.voice:
        is_voice_input = True
        await update.message.reply_text("\U0001F3A4 Listening...")
        voice_file = await update.message.voice.get_file()
        import tempfile, os as _os
        ogg_path = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False, dir="/tmp").name
        await voice_file.download_to_drive(ogg_path)
        from tools.voice_telegram import transcribe_ogg
        loop = asyncio.get_event_loop()
        user_msg = await loop.run_in_executor(None, transcribe_ogg, ogg_path)
        try:
            _os.remove(ogg_path)
        except Exception:
            pass
        if not user_msg:
            await update.message.reply_text("GAP: could not understand the voice message.")
            return

    # Video message handler — send to Gemini for analysis
    if not user_msg and update.message.video:
        await update.message.reply_text("🎬 Analyzing video...")
        video_file = await update.message.video.get_file()
        import tempfile, os as _os
        mp4_path = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False, dir="/tmp").name
        await video_file.download_to_drive(mp4_path)
        caption = update.message.caption or "Summarize what is happening in this video."
        from tools.video_tool import analyze_video
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, analyze_video, mp4_path, caption)
        try:
            _os.remove(mp4_path)
        except Exception:
            pass
        await update.message.reply_text(result[:4000])
        return

    if not user_msg:
        await update.message.reply_text("Send text for now — voice coming soon!")
        return

    await update.message.reply_text("⏳ thinking...")
    # Browser commands — bypass LLM, run sync playwright in thread
    from tools.dispatcher import detect_intent, run_tool
    _intent = detect_intent(user_msg)
    from tools.self_edit import has_pending_edit, confirm_pending_edit, cancel_pending_edit, propose_edit
    if has_pending_edit():
        if user_msg.strip().lower() in ("yes", "y", "confirm", "save"):
            response = confirm_pending_edit()
        else:
            response = cancel_pending_edit()
        await update.message.reply_text(response[:4000])
        return
    if user_msg.strip().startswith("/editfile "):
        from tools.self_edit import write_file
        parts = user_msg.strip()[len("/editfile "):].split("|||", 1)
        if len(parts) != 2:
            response = "Usage: /editfile <path>|||<new content>"
        else:
            response = write_file(parts[0].strip(), parts[1])
    elif user_msg.strip().startswith("/readfile "):
        from tools.self_edit import read_file
        response = read_file(user_msg.strip()[len("/readfile "):].strip())
    elif user_msg.strip().startswith("/listbackups"):
        from tools.self_edit import list_backups
        arg = user_msg.strip()[len("/listbackups"):].strip()
        response = list_backups(arg if arg else None)
    elif user_msg.strip().startswith("/restorebackup "):
        from tools.self_edit import restore_backup
        parts = user_msg.strip()[len("/restorebackup "):].split("|||", 1)
        if len(parts) != 2:
            response = "Usage: /restorebackup <backup_filename>|||<target_path>"
        else:
            response = restore_backup(parts[0].strip(), parts[1].strip())
    elif user_msg.strip().startswith("/edit "):
        instruction = user_msg.strip()[len("/edit "):].strip()
        response = propose_edit(instruction, engine.router if hasattr(engine, "router") else engine)
    elif _intent["tool"] == "browser":
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: run_tool(_intent, user_msg))
    else:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: engine.chat(user_msg))
    if response.startswith("Screenshot saved to "):
        img_path = response.split("Screenshot saved to ")[-1].strip()
        try:
            await update.message.reply_photo(photo=open(img_path, "rb"))
        except Exception as e:
            await update.message.reply_text(f"Screenshot taken but couldn't send image: {e}")
    elif response.startswith("IMAGE_GENERATED|"):
        img_path = response.split("IMAGE_GENERATED|", 1)[-1].strip()
        try:
            await update.message.reply_photo(photo=open(img_path, "rb"))
        except Exception as e:
            await update.message.reply_text(f"Image generated but couldn't send it: {e}")
    elif is_voice_input:
        await update.message.reply_text(response[:4000])
        from tools.voice_telegram import text_to_voice_ogg
        loop = asyncio.get_event_loop()
        voice_reply_path = await loop.run_in_executor(None, text_to_voice_ogg, response)
        if voice_reply_path:
            try:
                await update.message.reply_voice(voice=open(voice_reply_path, "rb"))
            except Exception:
                pass
            try:
                import os as _os
                _os.remove(voice_reply_path)
            except Exception:
                pass
    else:
        await update.message.reply_text(response[:4000])

async def _mcp_startup(app):
    try:
        from engine.mcp.mcp_client import _startup_connect
        await _startup_connect()
        print("[mcp] All MCP servers connected at startup.")
    except Exception as e:
        print(f"[mcp] Startup connection failed: {e}")

app = ApplicationBuilder().token(BOT_TOKEN).post_init(_mcp_startup).build()
async def handle_snooze(update, ctx):
    query = update.callback_query
    await query.answer()
    if update.effective_user.id != YOUR_ID:
        return
    data = query.data  # format: "snooze|<minutes>|<task>"
    parts = data.split("|", 2)
    if len(parts) != 3 or parts[0] != "snooze":
        return
    minutes = int(parts[1])
    task = parts[2]
    from datetime import datetime, timedelta
    import pytz, subprocess
    IST = pytz.timezone("Asia/Kolkata")
    remind_time = datetime.now(IST) + timedelta(minutes=minutes)
    at_time_str = remind_time.strftime("%H:%M %Y-%m-%d")
    notify_cmd = f'python3 /home/shrridharshan/shrri/tools/telegram_notify.py "⏰ SHRRI Reminder (snoozed): {task}"'
    subprocess.run(['at', at_time_str], input=notify_cmd, text=True, capture_output=True)
    await query.edit_message_text(f"⏰ Snoozed for {minutes} minutes — I'll remind you to: {task}")

app.add_handler(MessageHandler(filters.ALL, handle))
app.add_handler(CallbackQueryHandler(handle_snooze))
print("SHRRI Telegram bot running...")
app.run_polling()
