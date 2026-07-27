# -*- coding: utf-8 -*-
import requests
import json
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8770149502:AAFkmj14adoaUHCFHXcBO9aNwjjDdpcfuLY"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
captured_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 بوت استخراج الجلسات - للجميع!\n\n"
        "/capture <رابط>\n/list\n/use <id>\n/clear\n/help"
    )

async def capture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ أدخل رابط: /capture https://example.com")
        return
    url = context.args[0]
    try:
        response = requests.get(url, timeout=10)
        cookies = response.cookies.get_dict()
        headers = dict(response.headers)
        session_data = {
            "url": url,
            "cookies": cookies,
            "authorization": headers.get("Authorization", ""),
            "set_cookie": headers.get("Set-Cookie", "")
        }
        session_id = len(captured_sessions) + 1
        captured_sessions[session_id] = session_data
        await update.message.reply_text(
            f"✅ تم الاعتراض!\n🆔 المعرف: {session_id}\n🍪 الكوكيز: {cookies}\n🔑 التوكن: {session_data['authorization'][:30] if session_data['authorization'] else 'لا يوجد'}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ فشل: {str(e)}")

async def list_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not captured_sessions:
        await update.message.reply_text("📭 لا توجد جلسات.")
        return
    msg = "📋 الجلسات:\n\n"
    for sid, data in captured_sessions.items():
        msg += f"🆔 {sid} | {data['url']} | كوكيز: {len(data['cookies'])}\n"
    await update.message.reply_text(msg)

async def use_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ استخدم: /use 1")
        return
    try:
        sid = int(context.args[0])
        data = captured_sessions.get(sid)
        if not data:
            await update.message.reply_text("❌ غير موجود.")
            return
        output = f"🔓 جلسة #{sid}\n📍 الرابط: {data['url']}\n🍪 الكوكيز: {json.dumps(data['cookies'], indent=2)}\n🔑 التوكن: {data['authorization']}"
        await update.message.reply_text(output)
    except ValueError:
        await update.message.reply_text("⚠️ المعرف يجب أن يكون رقمًا.")

async def clear_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    captured_sessions.clear()
    await update.message.reply_text("🗑️ تم الحذف.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("capture", capture))
    app.add_handler(CommandHandler("list", list_sessions))
    app.add_handler(CommandHandler("use", use_session))
    app.add_handler(CommandHandler("clear", clear_sessions))
    app.add_handler(CommandHandler("help", help_command))
    print("🔥 البوت يعمل للجميع...")
    app.run_polling()

if __name__ == "__main__":
    main()
