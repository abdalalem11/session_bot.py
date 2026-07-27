import asyncio
import os
import sys
import subprocess
import json
import re
from datetime import datetime
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# ====== حل جذري لمشكلة Event Loop ======
try:
    asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# ====== استيراد Pyrogram ======
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

# ====== تكوين البوت ======
API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
WORK_DIR = os.getenv('WORK_DIR', '/tmp/sessions')
PORT = int(os.getenv('PORT', 10000))

if not API_ID or not API_HASH or not BOT_TOKEN:
    print("خطأ: تأكد من تعيين API_ID, API_HASH, BOT_TOKEN")
    sys.exit(1)

os.makedirs(WORK_DIR, exist_ok=True)

# ====== خادم HTTP للإبقاء على البوت نشطاً في Render ======
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    
    def log_message(self, format, *args):
        return  # تعطيل التسجيل لتقليل الضجيج

def run_health_server():
    try:
        server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
        server.serve_forever()
    except Exception as e:
        print(f"⚠️ خادم الصحة: {e}")

# تشغيل خادم الصحة في خيط منفصل
Thread(target=run_health_server, daemon=True).start()
print(f"✅ خادم الصحة يعمل على المنفذ {PORT}")

# ====== إنشاء عميل Pyrogram ======
app = Client(
    "main_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workdir=WORK_DIR
)

# ====== الأدوات المساعدة ======
def extract_tokens(text):
    patterns = {
        'Bot Token': r'\d+:[A-Za-z0-9_\-]{35,}',
        'API Key': r'[A-Za-z0-9]{32,}',
        'GitHub Token': r'gh[pous]_[A-Za-z0-9_]{36,}',
        'AWS Key': r'AKIA[0-9A-Z]{16}',
        'Telegram Session': r'\d+:[A-Za-z0-9_\-]{35,}',
        'JWT': r'eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+'
    }
    results = {}
    for name, pattern in patterns.items():
        matches = re.findall(pattern, text)
        if matches:
            results[name] = matches
    return results

def get_session_files():
    sessions = []
    for file in os.listdir(WORK_DIR):
        if file.endswith('.session') or file.endswith('.session-journal'):
            sessions.append(file)
    return sessions

def read_session_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read(500)
    except:
        return "لا يمكن قراءة الملف"

# ====== أزرار الإنلاين ======
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 استخراج الجلسات", callback_data="extract_sessions")],
        [InlineKeyboardButton("🔑 استخراج التوكنات", callback_data="extract_tokens")],
        [InlineKeyboardButton("📁 إدارة الملفات", callback_data="file_manager")],
        [InlineKeyboardButton("⚙️ تنفيذ أوامر", callback_data="exec_menu")],
        [InlineKeyboardButton("📊 معلومات النظام", callback_data="sys_info")]
    ])

def session_keyboard():
    sessions = get_session_files()
    keyboard = []
    for sess in sessions[:10]:
        keyboard.append([InlineKeyboardButton(f"📄 {sess}", callback_data=f"view_session:{sess}")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

# ====== معالج الأوامر ======
@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    welcome = f"""
🤖 **بوت التحكم المتقدم**

👋 مرحباً {message.from_user.first_name}!

**المميزات:**
✅ استخراج جلسات Telegram
✅ كشف التوكنات الحساسة
✅ إدارة الملفات
✅ تنفيذ الأوامر
✅ معلومات النظام

📌 استخدم الأزرار للتحكم.
"""
    await message.reply_text(welcome, reply_markup=main_keyboard())

@app.on_message(filters.command("exec"))
async def exec_command(client: Client, message: Message):
    cmd = message.text.replace('/exec', '').strip()
    if not cmd:
        await message.reply_text("⚠️ الرجاء إدخال أمر للتنفيذ\nمثال: `/exec ls -la`")
        return

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        if len(output) > 4000:
            output = output[:4000] + "\n\n... (مقتطع)"
        await message.reply_text(f"```\n{output}\n```" if output else "✅ تم التنفيذ بنجاح (بدون مخرجات)")
    except subprocess.TimeoutExpired:
        await message.reply_text("⏰ انتهت مهلة التنفيذ (30 ثانية)")
    except Exception as e:
        await message.reply_text(f"❌ خطأ: {str(e)}")

@app.on_message(filters.document & filters.private)
async def handle_file(client: Client, message: Message):
    try:
        file_path = await client.download_media(
            message.document,
            file_name=f"{WORK_DIR}/{message.document.file_name}"
        )
        await message.reply_text(f"✅ تم رفع الملف إلى:\n`{file_path}`")
    except Exception as e:
        await message.reply_text(f"❌ خطأ في الرفع: {str(e)}")

# ====== معالج استدعاء الأزرار ======
@app.on_callback_query()
async def handle_callback(client: Client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id
    message = callback_query.message

    await callback_query.answer()

    if data == "back_main":
        await message.edit_text("🏠 **القائمة الرئيسية**", reply_markup=main_keyboard())

    elif data == "extract_sessions":
        sessions = get_session_files()
        if not sessions:
            await message.edit_text("❌ لا توجد جلسات مخزنة.", reply_markup=main_keyboard())
            return

        text = "📦 **ملفات الجلسات الموجودة:**\n\n"
        for sess in sessions[:15]:
            size = os.path.getsize(f"{WORK_DIR}/{sess}")
            text += f"📄 `{sess}` ({size:,} بايت)\n"

        if len(sessions) > 15:
            text += f"\n... و {len(sessions) - 15} ملفات أخرى"

        await message.edit_text(text, reply_markup=session_keyboard())

    elif data.startswith("view_session:"):
        sess_name = data.split(":", 1)[1]
        file_path = f"{WORK_DIR}/{sess_name}"

        if not os.path.exists(file_path):
            await message.edit_text("❌ الملف غير موجود", reply_markup=session_keyboard())
            return

        content = read_session_file(file_path)
        text = f"📄 **الجلسة:** `{sess_name}`\n"
        text += f"📏 الحجم: {os.path.getsize(file_path):,} بايت\n"
        text += f"📅 التعديل: {datetime.fromtimestamp(os.path.getmtime(file_path))}\n\n"
        text += f"**المحتوى (جزء):**\n```\n{content}\n```"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 تحميل الملف", callback_data=f"download_session:{sess_name}")],
            [InlineKeyboardButton("🗑️ حذف الملف", callback_data=f"delete_session:{sess_name}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="extract_sessions")]
        ])
        await message.edit_text(text, reply_markup=buttons)

    elif data.startswith("download_session:"):
        sess_name = data.split(":", 1)[1]
        file_path = f"{WORK_DIR}/{sess_name}"

        if os.path.exists(file_path):
            await client.send_document(
                chat_id=user_id,
                document=file_path,
                caption=f"📎 `{sess_name}`"
            )
            await callback_query.answer("✅ جاري التحميل...", show_alert=True)
        else:
            await callback_query.answer("❌ الملف غير موجود", show_alert=True)

    elif data.startswith("delete_session:"):
        sess_name = data.split(":", 1)[1]
        file_path = f"{WORK_DIR}/{sess_name}"

        try:
            os.remove(file_path)
            await callback_query.answer("🗑️ تم حذف الملف", show_alert=True)
            await handle_callback(client, callback_query)
        except:
            await callback_query.answer("❌ فشل الحذف", show_alert=True)

    elif data == "extract_tokens":
        tokens_found = {}
        for file in os.listdir(WORK_DIR):
            if file.endswith('.txt') or file.endswith('.log') or file.endswith('.json'):
                file_path = f"{WORK_DIR}/{file}"
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(10000)
                        extracted = extract_tokens(content)
                        if extracted:
                            tokens_found[file] = extracted
                except:
                    pass

        if not tokens_found:
            await message.edit_text("🔍 **لم يتم العثور على توكنات**\n\n" +
                                   "💡 يمكنك رفع ملفات نصية للبحث فيها.",
                                   reply_markup=main_keyboard())
            return

        text = "🔑 **التوكنات المكتشفة:**\n\n"
        for file, tokens in tokens_found.items():
            text += f"📄 **{file}**\n"
            for token_type, token_list in tokens.items():
                text += f"  • {token_type}: `{token_list[0]}`"
                if len(token_list) > 1:
                    text += f" (+{len(token_list)-1} أخرى)"
                text += "\n"
            text += "\n"

        await message.edit_text(text[:4000], reply_markup=main_keyboard())

    elif data == "file_manager":
        files = os.listdir(WORK_DIR)[:20]
        if not files:
            await message.edit_text("📁 **لا توجد ملفات في الدليل**", reply_markup=main_keyboard())
            return

        text = "📁 **الملفات في الدليل:**\n\n"
        for f in files:
            f_path = f"{WORK_DIR}/{f}"
            if os.path.isfile(f_path):
                size = os.path.getsize(f_path)
                text += f"📄 `{f}` ({size:,} بايت)\n"
            else:
                text += f"📁 `{f}/`\n"

        await message.edit_text(text, reply_markup=main_keyboard())

    elif data == "exec_menu":
        await message.edit_text(
            "⚙️ **قائمة التنفيذ**\n\n"
            "استخدم الأمر `/exec <أمر>` لتنفيذ أي أمر شل.\n"
            "مثال: `/exec whoami`\n\n"
            "📌 **أوامر مفيدة:**\n"
            "• `ls -la` - عرض الملفات\n"
            "• `pwd` - الدليل الحالي\n"
            "• `whoami` - اسم المستخدم\n"
            "• `env` - المتغيرات البيئية",
            reply_markup=main_keyboard()
        )

    elif data == "sys_info":
        import platform
        info = f"""
📊 **معلومات النظام:**

🖥️ **النظام:** {platform.system()}
📅 **الإصدار:** {platform.release()}
🔧 **النسخة:** {platform.version()}
💻 **المعمارية:** {platform.machine()}
🧠 **المعالج:** {platform.processor() or 'غير متاح'}
🐍 **Python:** {platform.python_version()}

📁 **دليل العمل:** {WORK_DIR}
📦 **عدد الجلسات:** {len(get_session_files())}
📂 **الملفات:** {len(os.listdir(WORK_DIR))}
"""
        await message.edit_text(info, reply_markup=main_keyboard())

# ====== تشغيل البوت ======
async def main():
    print("🚀 بدء تشغيل البوت...")
    try:
        await app.start()
        me = await app.get_me()
        print(f"✅ البوت @{me.username} يعمل بنجاح!")
        print(f"📱 المعرف: {me.id}")
        print(f"📝 الاسم: {me.first_name or me.last_name or 'غير متاح'}")
        print("🔄 في انتظار الأوامر...")
        await asyncio.Event().wait()
    except Exception as e:
        print(f"❌ خطأ: {e}")
        raise
    finally:
        await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف البوت")
    except RuntimeError as e:
        print(f"⚠️ خطأ في الحلقة: {e}. محاولة التشغيل بطريقة بديلة...")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
