from aiogram import types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram.filters.command import Command
from services.achievement_service import get_user_achievements
from services.user_service import get_user_by_telegram


def register_myinfo_handlers(dp):
    @dp.message(Command("me"))
    async def get_my_information(message: types.Message):
        user = get_user_by_telegram(message.from_user.username)
        text = f"{user['username']}\n{user['bio']}"
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🏆 Достижения", callback_data="achievements"),
        )
        await message.answer(text, reply_markup=builder.as_markup())

    @dp.callback_query(F.data == "achievements")
    async def show_achievements(callback: types.CallbackQuery):
        user = get_user_by_telegram(callback.from_user.username)
        achievements = get_user_achievements(user['id'])
        text = "Ваши достижения:\n"
        for i in achievements:
            text += i['code'] + ' ' + i['emoji'] + '\n'
        await callback.message.edit_text(text)
        await callback.answer()


    @dp.callback_query(F.data == "back")
    async def go_back(callback: types.CallbackQuery):
        pass
