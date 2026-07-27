# -*- coding: utf-8 -*-
import requests
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = "8770149502:AAFkmj14adoaUHCFHXcBO9aNwjjDdpcfuLY"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
captured_sessions = {}

# ========== الأزرار ==========
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📥 اعتراض جلسة", callback_data="capture")],
        [InlineKeyboardButton("📋 عرض الجلسات", callback_data="list")],
        [InlineKeyboardButton("🗑️ حذف الكل", callback_data="clear")],
        [InlineKeyboardButton("❓ المساعدة", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ========== الأوامر ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 **بوت استخراج الجلسات**\n\n"
        "أرسل رابطاً وسأقوم باعتراض الجلسة.\n"
        "اختر من الأزرار أدناه:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

async def capture_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ أرسل الرابط بعد الأمر:\n`/اعتراض https://example.com`", parse_mode="Markdown")
        return
    await capture_url(update.message, context.args[0])

async def capture_url(message, url):
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
        await message.reply_text(
            f"✅ **تم الاعتراض!**\n"
            f"🆔 المعرف: `{session_id}`\n"
            f"🍪 الكوكيز: `{cookies}`\n"
            f"🔑 التوكن: `{session_data['authorization'][:30] if session_data['authorization'] else 'لا يوجد'}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.reply_text(f"❌ فشل الاعتراض: `{str(e)}`", parse_mode="Markdown")

async def list_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not captured_sessions:
        await update.message.reply_text("📭 لا توجد جلسات مخترقة.")
        return
    msg = "📋 **الجلسات المخترقة:**\n\n"
    for sid, data in captured_sessions.items():
        msg += f"🆔 `{sid}` | {data['url']} | كوكيز: {len(data['cookies'])}\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def use_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ استخدم: `/استخدام 1`", parse_mode="Markdown")
        return
    try:
        sid = int(context.args[0])
        data = captured_sessions.get(sid)
        if not data:
            await update.message.reply_text("❌ المعرف غير موجود.")
            return
        output = f"🔓 **جلسة #{sid}**\n📍 الرابط: {data['url']}\n🍪 الكوكيز:\n```json\n{json.dumps(data['cookies'], indent=2)}\n```\n🔑 التوكن: `{data['authorization']}`"
        await update.message.reply_text(output, parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("⚠️ المعرف يجب أن يكون رقمًا.")

async def clear_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    captured_sessions.clear()
    await update.message.reply_text("🗑️ تم حذف جميع الجلسات.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 **الأوامر:**\n"
        "/start - عرض الأزرار\n"
        "/اعتراض <رابط> - اعتراض جلسة\n"
        "/قائمة - عرض الجلسات\n"
        "/استخدام <id> - عرض جلسة\n"
        "/حذف - حذف الكل\n"
        "/مساعدة - هذه الرسالة",
        parse_mode="Markdown"
    )

# ========== معالجة الأزرار ==========
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "capture":
        await query.edit_message_text("📥 أرسل الرابط على شكل:\n`/اعتراض https://example.com`", parse_mode="Markdown")
    elif data == "list":
        if not captured_sessions:
            await query.edit_message_text("📭 لا توجد جلسات.")
            return
        msg = "📋 **الجلسات:**\n\n"
        for sid, info in captured_sessions.items():
            msg += f"🆔 `{sid}` | {info['url']} | كوكيز: {len(info['cookies'])}\n"
        await query.edit_message_text(msg, parse_mode="Markdown")
    elif data == "clear":
        captured_sessions.clear()
        await query.edit_message_text("🗑️ تم حذف الكل.")
    elif data == "help":
        await query.edit_message_text(
            "📖 **الأوامر:**\n"
            "/start - القائمة الرئيسية\n"
            "/اعتراض <رابط>\n"
            "/قائمة\n"
            "/استخدام <id>\n"
            "/حذف\n"
            "/مساعدة",
            parse_mode="Markdown"
        )

# ========== التشغيل ==========
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("اعتراض", capture_command))
    app.add_handler(CommandHandler("قائمة", list_sessions))
    app.add_handler(CommandHandler("استخدام", use_session))
    app.add_handler(CommandHandler("حذف", clear_sessions))
    app.add_handler(CommandHandler("مساعدة", help_command))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("🔥 البوت يعمل للجميع مع أزرار عربية...")
    app.run_polling()

if __name__ == "__main__":
    main()
