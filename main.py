import os
import asyncio
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from handlers.registration import register_handlers
from handlers.leader_boards import register_leadboard_handlers
from handlers.tests import register_tests_handlers
from handlers.my_info import register_myinfo_handlers

logging.basicConfig(level=logging.INFO)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("Токен бота не найден! Проверьте .env файл.")
bot = Bot(TOKEN)
dp = Dispatcher(storage=MemoryStorage())

register_handlers(dp)
register_leadboard_handlers(dp)
register_tests_handlers(dp)
register_myinfo_handlers(dp)

async def main():
    await bot.set_my_commands([
        BotCommand(command="start", description="Запуск бота"),
        BotCommand(command="leader_board", description="Посмотреть список лидеров"),
        BotCommand(command='me', description='Мой профиль'),
        BotCommand(command="tests", description="Начать тестирование"),
    ])
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())