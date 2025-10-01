import os
import logging
from telegram.ext import Updater, CommandHandler

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ ОШИБКА: Токен не найден!")
    exit(1)

print(f"✅ Токен получен, запускаю бота...")

def start(update, context):
    update.message.reply_text("🎉 Бот работает! Привет!")

def main():
    try:
        updater = Updater(BOT_TOKEN, use_context=True)
        dp = updater.dispatcher
        dp.add_handler(CommandHandler("start", start))
        
        print("✅ Бот запущен и готов к работе!")
        updater.start_polling()
        updater.idle()
    except Exception as e:
        print(f"❌ Ошибка при запуске: {e}")
        import time
        time.sleep(10)

if __name__ == "__main__":
    main()
