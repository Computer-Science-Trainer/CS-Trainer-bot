from aiogram import types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram.filters.command import Command
from httpx import HTTPStatusError
from .api_client import api_get, api_post
from messages.locale import messages


def register_userinfo(dp):
    @dp.message(Command("me"))
    async def get_my_information(message: types.Message):
        username = message.from_user.username
        try:
            login = await api_post('auth/login-telegram', {'telegram_username': username})
            name = login.get('username', username)
            user = await api_get(f"user/{name}")
            text = f"{user.get('username','')}\n{user.get('bio','')}"
        except HTTPStatusError:
            await message.answer(messages["registration"]["connectionError"])
            return
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="🏆 " + messages["profile"]["achievementsTab"],
                callback_data="achievements"),
        )
        await message.answer(text, reply_markup=builder.as_markup())

    @dp.callback_query(F.data == "achievements")
    async def show_achievements(callback: types.CallbackQuery):
        username = callback.from_user.username
        try:
            login = await api_post('auth/login-telegram', {'telegram_username': username})
            name = login.get('username', username)
            achievements = await api_get(f"user/{name}/achievements")
        except HTTPStatusError:
            await callback.message.answer(messages["registration"]["connectionError"])
            await callback.answer()
            return
        text = messages["profile"]["achievementsTab"] + ":\n"
        for i in achievements:
            ach = messages["profile"]["achievements"].get(i['code'])
            if ach:
                text += f"{i['emoji']} {ach['title']}: {ach['description']}\n"
            else:
                text += f"{i['emoji']} {i['code']}\n"
        await callback.message.edit_text(text)
        await callback.answer()

    @dp.callback_query(F.data == "back")
    async def go_back(callback: types.CallbackQuery):
        await callback.answer()
