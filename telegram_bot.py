import os, sys, asyncio, logging
sys.path.insert(0, os.path.expanduser("~/shrri"))

BOT_TOKEN = "8883988277:AAGAIFnGvTiApkyMVVTKwHB3_ioiQm7oLUE"
YOUR_ID = 6327084680  # paste your Telegram user ID here

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from engine import SHRRIEngine

engine = SHRRIEngine()
logging.basicConfig(level=logging.WARNING)

async def handle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # Security — only respond to you
    if update.effective_user.id != YOUR_ID:
        return

    user_msg = update.message.text or ""
    if not user_msg:
        await update.message.reply_text("Send text for now — voice coming soon!")
        return

    await update.message.reply_text("⏳ thinking...")
    # Browser commands — bypass LLM, run sync playwright in thread
    from tools.dispatcher import detect_intent, run_tool
    import asyncio
    _intent = detect_intent(user_msg)
    if _intent["tool"] == "browser":
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: run_tool(_intent, user_msg))
    else:
        response = engine.chat(user_msg)
    if response.startswith("Screenshot saved to "):
        img_path = response.split("Screenshot saved to ")[-1].strip()
        try:
            await update.message.reply_photo(photo=open(img_path, "rb"))
        except Exception as e:
            await update.message.reply_text(f"Screenshot taken but couldn't send image: {e}")
    else:
        await update.message.reply_text(response[:4000])

app = ApplicationBuilder().token(BOT_TOKEN).build()
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
