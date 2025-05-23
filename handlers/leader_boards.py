from aiogram import types
from stations import LeaderBoard
from aiogram.fsm.context import FSMContext
from services.leaderboard_service import get_leaderboard
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters.command import Command

def register_leadboard_handlers(dp):
    @dp.message(Command("leader_board"))
    async def getting_leaderboard(message: types.Message, state: FSMContext):
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="5"), KeyboardButton(text="10")]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )

        await message.answer(
            "Сколько лидеров вам показать?",
            reply_markup=keyboard
        )
        await state.set_state(LeaderBoard.quantity)

    @dp.message(LeaderBoard.quantity)
    async def get_quantity(message: types.Message, state: FSMContext):
        if message.text not in ["5", "10"]:
            await message.answer("Пожалуйста, выберите 5 или 10")
            return
        await state.update_data(quantity=int(message.text))
        topics_kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Алгоритмы")],
                [KeyboardButton(text="Фундаментальная информатика")]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer(
            "По какой теме показать лидеров?",
            reply_markup=topics_kb
        )
        await state.set_state(LeaderBoard.topic)

    @dp.message(LeaderBoard.topic)
    async def get_kind(message: types.Message, state: FSMContext):
        if message.text not in ["Алгоритмы", "Фундаментальная информатика"]:
            await message.answer("Пожалуйста, выберите тему из предложенных")
            return
        await state.update_data(topic=message.text)
        data = await state.get_data()
        if data['topic'] == 'Алгоритмы':
            topic = 'algorithms'
        else:
            topic = 'fundamentals'
        leaders = get_leaderboard(data['quantity'])[topic]
        text = f"Топ-{data['quantity']} лидеров по теме '{data['topic']}':\n"
        for i in leaders:
            text += i['username'] + ' ' + str(i['score']) + '\n'
        await message.answer(text, reply_markup=types.ReplyKeyboardRemove())
        await state.clear()