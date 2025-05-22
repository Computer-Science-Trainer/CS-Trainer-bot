import os
import asyncio
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from handlers.registration import register_handlers
from handlers.test_commands import register_test_handlers

logging.basicConfig(level=logging.INFO)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("Токен бота не найден! Проверьте .env файл.")
bot = Bot(TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Register handlers
register_handlers(dp)
register_test_handlers(dp)

async def main():
    await bot.set_my_commands([
        BotCommand(command="start", description="Запуск бота"),
        BotCommand(command="test1", description="Тестовая команда 1"),
    ])
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())