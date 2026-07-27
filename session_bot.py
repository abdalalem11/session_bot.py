# -*- coding: utf-8 -*-
# session_bot_pro.py
# بوت احترافي لاستخراج جلسات Telethon و Pyrogram مع أزرار Inline

import os
import re
import json
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telethon import TelegramClient, errors
from pyrogram import Client as PyroClient
from pyrogram.errors import ApiIdInvalid, PhoneNumberInvalid, PasswordHashInvalid

# ========== التوكنات (ضع توكنات البوتات هنا) ==========
BOT_TOKENS = [
    "8770149502:AAFkmj14adoaUHCFHXcBO9aNwjjDdpcfuLY",  # البوت الرئيسي
    # أضف توكنات بوتات أخرى هنا إذا أردت
]
# =====================================================

# ========== معرف المطورين (ضع معرفات التليجرام هنا) ==========
DEVELOPER_IDS = [1170411845]  # أضف معرفات إضافية هنا
# =============================================================

# تفعيل التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# قاعدة بيانات الجلسات
sessions_db = {}

# ========== دوال مساعدة ==========
def is_developer(user_id):
    return user_id in DEVELOPER_IDS

def format_session(session_data):
    output = f"📱 **جلسة {session_data['type'].upper()}**\n"
    output += f"🆔 المعرف: `{session_data['user_id']}`\n"
    output += f"📛 الاسم: {session_data.get('first_name', 'غير معروف')}\n"
    output += f"🔗 التاريخ: {session_data.get('date', datetime.now().strftime('%Y-%m-%d %H:%M'))}\n"
    output += f"📦 الجلسة:\n`{session_data['session_string'][:100]}...`"
    return output

# ========== الأزرار الرئيسية ==========
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📱 استخراج جلسة Telethon", callback_data="extract_telethon")],
        [InlineKeyboardButton("🐍 استخراج جلسة Pyrogram", callback_data="extract_pyrogram")],
        [InlineKeyboardButton("📋 عرض الجلسات", callback_data="list_sessions")],
        [InlineKeyboardButton("🗑️ حذف جلسة", callback_data="delete_session")],
        [InlineKeyboardButton("⚙️ إعدادات المطور", callback_data="dev_settings")],
        [InlineKeyboardButton("❓ المساعدة", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="main_menu")]
    ])

def get_confirm_keyboard(session_id, action):
    keyboard = [
        [
            InlineKeyboardButton("✅ تأكيد", callback_data=f"confirm_{action}_{session_id}"),
            InlineKeyboardButton("❌ إلغاء", callback_data=f"cancel_{action}_{session_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ========== بدء البوت ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data['step'] = None
    welcome = (
        "🔥 **بوت استخراج الجلسات الاحترافي**\n\n"
        "يمكنك استخراج جلسات Telethon و Pyrogram بسهولة.\n"
        "اختر الخدمة من الأزرار أدناه:"
    )
    await update.message.reply_text(welcome, reply_markup=get_main_keyboard(), parse_mode="Markdown")

# ========== استخراج جلسة Telethon ==========
async def extract_telethon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data['extract_type'] = 'telethon'
    context.user_data['step'] = 'await_api_id'
    await update.callback_query.message.reply_text(
        "📱 **استخراج جلسة Telethon**\n\n"
        "الرجاء إدخال **API ID** الخاص بك:\n"
        "(يمكنك الحصول عليه من https://my.telegram.org)",
        parse_mode="Markdown"
    )
    await update.callback_query.answer()

# ========== استخراج جلسة Pyrogram ==========
async def extract_pyrogram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data['extract_type'] = 'pyrogram'
    context.user_data['step'] = 'await_api_id'
    await update.callback_query.message.reply_text(
        "🐍 **استخراج جلسة Pyrogram**\n\n"
        "الرجاء إدخال **API ID** الخاص بك:\n"
        "(يمكنك الحصول عليه من https://my.telegram.org)",
        parse_mode="Markdown"
    )
    await update.callback_query.answer()

# ========== معالجة رسائل المستخدم ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    step = context.user_data.get('step')

    if step == 'await_api_id':
        if not text.isdigit():
            await update.message.reply_text("⚠️ API ID يجب أن يكون أرقاماً فقط. أعد المحاولة:")
            return
        context.user_data['api_id'] = int(text)
        context.user_data['step'] = 'await_api_hash'
        await update.message.reply_text("🔐 الآن أرسل **API Hash**:", parse_mode="Markdown")

    elif step == 'await_api_hash':
        if len(text) < 10:
            await update.message.reply_text("⚠️ API Hash غير صالح (يجب أن يكون أطول من 10 أحرف). أعد المحاولة:")
            return
        context.user_data['api_hash'] = text
        context.user_data['step'] = 'await_phone'
        await update.message.reply_text("📱 أرسل **رقم الهاتف** بالصيغة الدولية:\nمثال: `+966501234567`", parse_mode="Markdown")

    elif step == 'await_phone':
        phone = text.replace(' ', '').replace('-', '')
        if not re.match(r'^\+?\d{8,15}$', phone):
            await update.message.reply_text("⚠️ رقم الهاتف غير صالح. أعد المحاولة (مثال: +966501234567):")
            return
        context.user_data['phone'] = phone
        context.user_data['step'] = 'await_code'

        # إرسال رمز التحقق حسب النوع
        extract_type = context.user_data.get('extract_type')
        try:
            if extract_type == 'telethon':
                client = TelegramClient(
                    f"temp_{user_id}",
                    context.user_data['api_id'],
                    context.user_data['api_hash']
                )
                await client.connect()
                await client.send_code_request(phone)
                context.user_data['client'] = client
                await update.message.reply_text(
                    "📨 تم إرسال رمز التحقق إلى هاتفك.\n"
                    "أدخل الرمز (بالأرقام فقط):",
                    parse_mode="Markdown"
                )
            elif extract_type == 'pyrogram':
                client = PyroClient(
                    f"temp_{user_id}",
                    api_id=context.user_data['api_id'],
                    api_hash=context.user_data['api_hash'],
                    in_memory=True
                )
                await client.connect()
                result = await client.send_code(phone)
                context.user_data['client'] = client
                context.user_data['phone_code_hash'] = result.phone_code_hash
                await update.message.reply_text(
                    "📨 تم إرسال رمز التحقق إلى هاتفك.\n"
                    "أدخل الرمز (بالأرقام فقط):",
                    parse_mode="Markdown"
                )
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {str(e)}")
            context.user_data['step'] = None

    elif step == 'await_code':
        if not text.isdigit() or len(text) < 3:
            await update.message.reply_text("⚠️ الرمز يجب أن يكون أرقاماً فقط (3-8 أرقام). أعد المحاولة:")
            return

        extract_type = context.user_data.get('extract_type')
        client = context.user_data.get('client')
        try:
            if extract_type == 'telethon':
                await client.sign_in(
                    context.user_data['phone'],
                    int(text),
                    password=None
                )
                session_string = client.session.save()
                me = await client.get_me()
                session_data = {
                    'type': 'telethon',
                    'session_string': session_string,
                    'user_id': me.id,
                    'first_name': me.first_name,
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M')
                }
                sessions_db[session_data['user_id']] = session_data
                await client.disconnect()
                await update.message.reply_text(
                    f"✅ **تم استخراج الجلسة بنجاح!**\n\n"
                    f"{format_session(session_data)}\n\n"
                    "⚠️ احتفظ بالجلسة في مكان آمن.",
                    parse_mode="Markdown",
                    reply_markup=get_back_keyboard()
                )

            elif extract_type == 'pyrogram':
                await client.sign_in(
                    context.user_data['phone'],
                    context.user_data['phone_code_hash'],
                    int(text)
                )
                session_string = await client.export_session_string()
                me = await client.get_me()
                session_data = {
                    'type': 'pyrogram',
                    'session_string': session_string,
                    'user_id': me.id,
                    'first_name': me.first_name,
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M')
                }
                sessions_db[session_data['user_id']] = session_data
                await client.disconnect()
                await update.message.reply_text(
                    f"✅ **تم استخراج الجلسة بنجاح!**\n\n"
                    f"{format_session(session_data)}\n\n"
                    "⚠️ احتفظ بالجلسة في مكان آمن.",
                    parse_mode="Markdown",
                    reply_markup=get_back_keyboard()
                )

        except errors.PasswordHashInvalid:
            await update.message.reply_text("🔑 أرسل **كلمة مرور التحقق بخطوتين**:")
            context.user_data['step'] = 'await_password'
        except errors.FloodWaitError as e:
            await update.message.reply_text(f"⏳ انتظر {e.seconds} ثانية قبل إعادة المحاولة.")
        except Exception as e:
            await update.message.reply_text(f"❌ فشل: {str(e)}")
        finally:
            context.user_data['step'] = None

    elif step == 'await_password':
        password = text
        extract_type = context.user_data.get('extract_type')
        client = context.user_data.get('client')
        try:
            if extract_type == 'telethon':
                await client.sign_in(password=password)
                session_string = client.session.save()
                me = await client.get_me()
                session_data = {
                    'type': 'telethon',
                    'session_string': session_string,
                    'user_id': me.id,
                    'first_name': me.first_name,
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M')
                }
                sessions_db[session_data['user_id']] = session_data
                await client.disconnect()
                await update.message.reply_text(
                    f"✅ **تم استخراج الجلسة!**\n\n{format_session(session_data)}",
                    parse_mode="Markdown",
                    reply_markup=get_back_keyboard()
                )
            elif extract_type == 'pyrogram':
                await client.sign_in(password=password)
                session_string = await client.export_session_string()
                me = await client.get_me()
                session_data = {
                    'type': 'pyrogram',
                    'session_string': session_string,
                    'user_id': me.id,
                    'first_name': me.first_name,
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M')
                }
                sessions_db[session_data['user_id']] = session_data
                await client.disconnect()
                await update.message.reply_text(
                    f"✅ **تم استخراج الجلسة!**\n\n{format_session(session_data)}",
                    parse_mode="Markdown",
                    reply_markup=get_back_keyboard()
                )
        except Exception as e:
            await update.message.reply_text(f"❌ فشل: {str(e)}")
        finally:
            context.user_data['step'] = None

# ========== عرض الجلسات ==========
async def list_sessions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not sessions_db:
        await update.callback_query.message.reply_text(
            "📭 لا توجد جلسات محفوظة.",
            reply_markup=get_back_keyboard()
        )
        await update.callback_query.answer()
        return

    msg = "📋 **الجلسات المحفوظة:**\n\n"
    for uid, data in sessions_db.items():
        msg += f"🆔 `{uid}` | {data['type'].upper()} | {data.get('first_name', 'غير معروف')}\n"
    await update.callback_query.message.reply_text(
        msg,
        parse_mode="Markdown",
        reply_markup=get_back_keyboard()
    )
    await update.callback_query.answer()

# ========== حذف جلسة ==========
async def delete_session_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not sessions_db:
        await update.callback_query.message.reply_text(
            "📭 لا توجد جلسات لحذفها.",
            reply_markup=get_back_keyboard()
        )
        await update.callback_query.answer()
        return

    keyboard = []
    for uid, data in sessions_db.items():
        keyboard.append([
            InlineKeyboardButton(
                f"🗑️ {uid} - {data.get('first_name', 'غير معروف')}",
                callback_data=f"del_{uid}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 إلغاء", callback_data="main_menu")])
    await update.callback_query.message.reply_text(
        "اختر الجلسة لحذفها:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await update.callback_query.answer()

# ========== تأكيد الحذف ==========
async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = int(query.data.split('_')[1])
    if uid in sessions_db:
        del sessions_db[uid]
        await query.message.edit_text(
            f"✅ تم حذف الجلسة `{uid}`.",
            reply_markup=get_back_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await query.message.edit_text(
            "❌ الجلسة غير موجودة.",
            reply_markup=get_back_keyboard()
        )
    await query.answer()

# ========== إعدادات المطور ==========
async def dev_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_developer(user_id):
        await update.callback_query.message.reply_text("🚫 غير مصرح.")
        await update.callback_query.answer()
        return

    keyboard = [
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="stats")],
        [InlineKeyboardButton("🗑️ حذف الكل", callback_data="clear_all")],
        [InlineKeyboardButton("📤 تصدير الجلسات", callback_data="export_sessions")],
        [InlineKeyboardButton("🔙 العودة", callback_data="main_menu")]
    ]
    await update.callback_query.message.edit_text(
        "⚙️ **لوحة تحكم المطور**\n\n"
        "اختر الإجراء:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    await update.callback_query.answer()

# ========== إحصائيات ==========
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_developer(user_id):
        await update.callback_query.answer("🚫 غير مصرح.", show_alert=True)
        return

    total = len(sessions_db)
    telethon_count = sum(1 for s in sessions_db.values() if s['type'] == 'telethon')
    pyrogram_count = sum(1 for s in sessions_db.values() if s['type'] == 'pyrogram')

    msg = (
        "📊 **الإحصائيات**\n\n"
        f"📱 إجمالي الجلسات: `{total}`\n"
        f"🔵 Telethon: `{telethon_count}`\n"
        f"🟢 Pyrogram: `{pyrogram_count}`"
    )
    await update.callback_query.message.edit_text(
        msg,
        parse_mode="Markdown",
        reply_markup=get_back_keyboard()
    )
    await update.callback_query.answer()

# ========== تصدير الجلسات ==========
async def export_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_developer(user_id):
        await update.callback_query.answer("🚫 غير مصرح.", show_alert=True)
        return

    if not sessions_db:
        await update.callback_query.message.reply_text("📭 لا توجد جلسات.")
        return

    export_data = json.dumps(sessions_db, indent=2, default=str)
    # تقطيع النص الطويل
    max_len = 4000
    for i in range(0, len(export_data), max_len):
        chunk = export_data[i:i+max_len]
        await update.callback_query.message.reply_text(
            f"```json\n{chunk}\n```",
            parse_mode="Markdown"
        )
    await update.callback_query.answer()

# ========== حذف الكل ==========
async def clear_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_developer(user_id):
        await update.callback_query.answer("🚫 غير مصرح.", show_alert=True)
        return

    sessions_db.clear()
    await update.callback_query.message.edit_text(
        "🗑️ تم حذف جميع الجلسات.",
        reply_markup=get_back_keyboard()
    )
    await update.callback_query.answer()

# ========== أزرار التنقل ==========
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.edit_text(
        "🔥 **القائمة الرئيسية**\n\nاختر الخدمة:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
    await update.callback_query.answer()

async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.edit_text(
        "❓ **المساعدة**\n\n"
        "1️⃣ اضغط على 'استخراج جلسة' واتبع التعليمات.\n"
        "2️⃣ أدخل API ID و API Hash من my.telegram.org.\n"
        "3️⃣ أدخل رقم هاتفك.\n"
        "4️⃣ أدخل رمز التحقق الذي سيصلك.\n"
        "5️⃣ سيتم عرض الجلسة.\n\n"
        "⚠️ استخدم بحذر، ولا تشارك جلساتك مع أحد.",
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown"
    )
    await update.callback_query.answer()

# ========== تشغيل البوت ==========
def main():
    if not BOT_TOKENS:
        logger.error("لم يتم تعيين أي توكن للبوت!")
        return

    for token in BOT_TOKENS:
        app = Application.builder().token(token).build()

        # الأوامر
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # الأزرار
        app.add_handler(CallbackQueryHandler(extract_telethon, pattern="^extract_telethon$"))
        app.add_handler(CallbackQueryHandler(extract_pyrogram, pattern="^extract_pyrogram$"))
        app.add_handler(CallbackQueryHandler(list_sessions_callback, pattern="^list_sessions$"))
        app.add_handler(CallbackQueryHandler(delete_session_callback, pattern="^delete_session$"))
        app.add_handler(CallbackQueryHandler(dev_settings, pattern="^dev_settings$"))
        app.add_handler(CallbackQueryHandler(main_menu, pattern="^main_menu$"))
        app.add_handler(CallbackQueryHandler(help_callback, pattern="^help$"))
        app.add_handler(CallbackQueryHandler(stats, pattern="^stats$"))
        app.add_handler(CallbackQueryHandler(export_sessions, pattern="^export_sessions$"))
        app.add_handler(CallbackQueryHandler(clear_all, pattern="^clear_all$"))
        app.add_handler(CallbackQueryHandler(confirm_delete, pattern=r"^del_\d+$"))

        # تشغيل البوت
        logger.info(f"🔥 تشغيل البوت بالتوكن: {token[:10]}...")
        app.run_polling()

if __name__ == "__main__":
    main()
