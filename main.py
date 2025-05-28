import os
import asyncio
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from handlers.registration import register_registration
from handlers.leaderboard import register_leaderboard
from handlers.tests import register_tests
from handlers.user_info import register_userinfo
from messages.locale import messages

logging.basicConfig(level=logging.INFO)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError(messages["main"]["tokenMissing"])
bot = Bot(TOKEN)
dp = Dispatcher(storage=MemoryStorage())

register_registration(dp)
register_leaderboard(dp)
register_tests(dp)
register_userinfo(dp)

async def main():
    await bot.set_my_commands([
        BotCommand(command="start", description=messages["main"]["commands"]["start"]),
        BotCommand(command="leaderboard", description=messages["main"]["commands"]["leaderboard"]),
        BotCommand(command='me', description=messages["main"]["commands"]["me"]),
        BotCommand(command="tests", description=messages["main"]["commands"]["tests"]),
    ])
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
