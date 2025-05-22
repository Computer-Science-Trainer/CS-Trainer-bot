from aiogram import types
from stations import Tests
from aiogram.fsm.context import FSMContext
from services.leaderboard_service import get_leaderboard
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters.command import Command

def register_tests_handlers(dp):
    @dp.message(Command("tests"))
    async def getting_leaderboard(message: types.Message, state: FSMContext):
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Рекомендованный"), KeyboardButton(text="Создам сам")]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer(
            "Выбери тип теста?",
            reply_markup=keyboard
        )
        await state.set_state(Tests.type_of_test)

    @dp.message(Command("tests"))
    async def get_type_of_test(message: types.Message, state: FSMContext):
        await state.update_data(type_of_tests=message.text)
        if message.text not in ["Рекомендованный", "Создам сам"]:
            await message.answer("Пожалуйста, выберите тип из предложенных")
            return
        if message.text == 'Рекомендованный':
            await message.answer('')
            await state.set_state(Tests.recommended_test)
        else:
            await message.answer('Выбери темы для вопросов')
            await state.set_state(Tests.topic)