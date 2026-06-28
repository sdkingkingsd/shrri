import os, sys, asyncio, logging
sys.path.insert(0, os.path.expanduser("~/shrri"))

BOT_TOKEN = "8883988277:AAGAIFnGvTiApkyMVVTKwHB3_ioiQm7oLUE"
YOUR_ID = 6327084680  # paste your Telegram user ID here

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
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
    response = engine.chat(user_msg)
    await update.message.reply_text(response[:4000])

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.ALL, handle))
print("SHRRI Telegram bot running...")
app.run_polling()
