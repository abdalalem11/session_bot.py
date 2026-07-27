# -*- coding: utf-8 -*-
# bot_session_hijacker.py
# ملف واحد لتشغيل البوت

import requests
import re
import json
import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ======== الإعدادات ========
BOT_TOKEN = "8770149502:AAFkmj14adoaUHCFHXcBO9aNwjjDdpcfuLY"
DEVELOPER_ID = 1170411845  # تم التحديث
# ===========================

# تفعيل التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# قاعدة بيانات الجلسات
captured_sessions = {}

# ========== الأوامر ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DEVELOPER_ID:
        await update.message.reply_text("🚫 غير مصرح.")
        return
    await update.message.reply_text(
        "🔥 مرحباً أيها المطور.\n\n"
        "الأوامر:\n"
        "/capture <رابط> - اعتراض جلسة\n"
        "/list - عرض الجلسات\n"
        "/use <id> - استخدام جلسة\n"
        "/clear - حذف الكل\n"
        "/help - المساعدة"
    )

async def capture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DEVELOPER_ID:
        await update.message.reply_text("🚫 غير مصرح.")
        return

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
            f"✅ تم الاعتراض!\n"
            f"🆔 المعرف: {session_id}\n"
            f"🍪 الكوكيز: {cookies}\n"
            f"🔑 التوكن: {session_data['authorization'][:30] if session_data['authorization'] else 'لا يوجد'}"
        )

    except Exception as e:
        await update.message.reply_text(f"❌ فشل: {str(e)}")

async def list_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DEVELOPER_ID:
        await update.message.reply_text("🚫 غير مصرح.")
        return

    if not captured_sessions:
        await update.message.reply_text("📭 لا توجد جلسات.")
        return

    msg = "📋 الجلسات:\n\n"
    for sid, data in captured_sessions.items():
        msg += f"🆔 {sid} | {data['url']} | كوكيز: {len(data['cookies'])}\n"
    await update.message.reply_text(msg)

async def use_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DEVELOPER_ID:
        await update.message.reply_text("🚫 غير مصرح.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ استخدم: /use 1")
        return

    try:
        sid = int(context.args[0])
        data = captured_sessions.get(sid)
        if not data:
            await update.message.reply_text("❌ غير موجود.")
            return

        output = f"🔓 جلسة #{sid}\n"
        output += f"📍 الرابط: {data['url']}\n"
        output += f"🍪 الكوكيز: {json.dumps(data['cookies'], indent=2)}\n"
        output += f"🔑 التوكن: {data['authorization']}\n"
        await update.message.reply_text(output)

    except ValueError:
        await update.message.reply_text("⚠️ المعرف يجب أن يكون رقمًا.")

async def clear_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DEVELOPER_ID:
        await update.message.reply_text("🚫 غير مصرح.")
        return

    captured_sessions.clear()
    await update.message.reply_text("🗑️ تم الحذف.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

# ========== التشغيل ==========
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("capture", capture))
    app.add_handler(CommandHandler("list", list_sessions))
    app.add_handler(CommandHandler("use", use_session))
    app.add_handler(CommandHandler("clear", clear_sessions))
    app.add_handler(CommandHandler("help", help_command))

    print("🔥 البوت يعمل...")
    app.run_polling()

if __name__ == "__main__":
    main()
