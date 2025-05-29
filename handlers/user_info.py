from aiogram import types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from .api_client import api_get, api_post
from messages.locale import messages


async def fetch_user_data(telegram_username):
    login = await api_post('auth/login-telegram', {'telegram_username': telegram_username})
    name = login.get('username', telegram_username)
    user = await api_get(f"user/{name}")
    stats = await api_get(f"user/{name}/stats")
    return user, stats


def build_profile_text(user, stats):
    bio = user.get('bio', '')
    text = f"👤 <b>{user.get('username','')}</b>\n"
    if bio:
        text += f"📝 {bio}\n\n"
    text += (
        f"<b>📊 Статистика:</b>\n"
        f"• Пройдено: <b>{stats.get('passed',0)}</b> из <b>{stats.get('total',0)}</b> задач\n"
        f"• Средний результат: <b>{round(stats.get('average',0)*100,1)}%</b>\n"
        f"• ФИ: <b>{stats.get('fundamentals',0)}</b>\n"
        f"• АиСД: <b>{stats.get('algorithms',0)}</b>\n"
    )
    return text


def profile_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🏆 " + messages["profile"]["achievementsTab"],
            callback_data="achievements"
        )
    )
    return builder.as_markup()


def show_main_profile_handler(dp):
    async def get_my_information(message: types.Message):
        await show_profile(message)


async def show_profile(message):
    user, stats = await fetch_user_data(message.chat.username)
    await message.answer(
        build_profile_text(user, stats),
        reply_markup=profile_keyboard(),
        parse_mode="HTML"
    )


def register_userinfo(dp):
    show_main_profile_handler(dp)

    @dp.callback_query(F.data == "achievements")
    async def show_achievements(callback: types.CallbackQuery):
        username = callback.from_user.username
        login = await api_post('auth/login-telegram', {'telegram_username': username})
        name = login.get('username', username)
        achievements = await api_get(f"user/{name}/achievements")
        text = messages["profile"]["achievementsTab"] + ":\n"
        for i in achievements:
            ach = messages["profile"]["achievements"].get(i['code'])
            text += f"{i['emoji']} {ach['title']}: {ach['description']}\n"
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Назад", callback_data="back")
        builder.adjust(1)
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.answer()

    @dp.callback_query(F.data == "back")
    async def go_back(callback: types.CallbackQuery):
        await callback.answer()
        user, stats = await fetch_user_data(callback.from_user.username)
        await callback.message.edit_text(
            build_profile_text(user, stats),
            reply_markup=profile_keyboard(),
            parse_mode="HTML"
        )
