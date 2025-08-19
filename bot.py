import logging
import random
import asyncio
import qrcode
import io
import os
from telegram import Update, InputFile
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from deep_translator import GoogleTranslator
from gtts import gTTS
import matplotlib.pyplot as plt
from datetime import datetime
import pytz

# توکن ربات
TOKEN = "8362717235:AAFCsg23PWE3LQXdxVxB0I_gAgkU1P3fMvQ"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# برای چت ناشناس
waiting_users = []
active_chats = {}

# دستورات پایه
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! من یه ربات همه‌کاره‌ام. از /help استفاده کن.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        """/start - شروع
/help - لیست دستورات
/tr متن - ترجمه به انگلیسی
/voice متن - تبدیل متن به صدا
/qrcode متن - تولید QR
/joke - جوک رندوم
/find - شروع چت ناشناس
/next - جفت بعدی
/stop - خروج از چت ناشناس"""
    )

# ترجمه
async def tr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("لطفا متنی وارد کنید")
        return
    text = " ".join(context.args)
    translated = GoogleTranslator(source="auto", target="en").translate(text)
    await update.message.reply_text(f"✅ ترجمه:\n{translated}")

# تبدیل متن به صدا
async def voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("لطفا متنی وارد کنید")
        return
    tts = gTTS(text=text, lang="fa")
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    await update.message.reply_voice(voice=buf)

# QR Code
async def make_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("لطفا متنی وارد کنید")
        return
    img = qrcode.make(text)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    await update.message.reply_photo(photo=buf)

# جوک
async def joke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jokes = ["یه جوک خنده‌دار 😂", "اینم یه شوخی ساده 😅", "خنده بر هر درد بی‌درمان دواست 😁"]
    await update.message.reply_text(random.choice(jokes))

# چت ناشناس
async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        await update.message.reply_text("شما در حال حاضر توی یه چت هستید. /stop بزنید")
        return
    if waiting_users and waiting_users[0] != user_id:
        partner_id = waiting_users.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        await update.message.reply_text("✅ جفت پیدا شد!")
        await context.bot.send_message(partner_id, "یه نفر بهت وصل شد! 👋")
    else:
        waiting_users.append(user_id)
        await update.message.reply_text("⏳ منتظر بمون تا یه جفت پیدا بشه...")

async def next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await stop(update, context)
    await find(update, context)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        await update.message.reply_text("چت ناشناس پایان یافت ❌")
        await context.bot.send_message(partner_id, "طرف مقابل چت رو ترک کرد 😢")
    elif user_id in waiting_users:
        waiting_users.remove(user_id)
        await update.message.reply_text("از صف انتظار خارج شدید ✅")
    else:
        await update.message.reply_text("شما توی هیچ چتی نیستید.")

async def relay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        if update.message.text:
            await context.bot.send_message(partner_id, update.message.text)
        elif update.message.photo:
            photo = update.message.photo[-1]
            file = await photo.get_file()
            await context.bot.send_photo(partner_id, file.file_id)

# نسخه مخصوص Render (Webhook)
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("tr", tr))
    app.add_handler(CommandHandler("voice", voice))
    app.add_handler(CommandHandler("qrcode", make_qr))
    app.add_handler(CommandHandler("joke", joke))
    app.add_handler(CommandHandler("find", find))
    app.add_handler(CommandHandler("next", next))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, relay))

    # این قسمت برای Render
    port = int(os.environ.get("PORT", 8443))
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    )

if __name__ == "__main__":
    main()
