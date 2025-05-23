from aiogram import types, F
from stations import Tests
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.command import Command
from services.test_service import get_test, update_questions, get_questions
from services.user_service import get_user_by_telegram, save_user_test

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

    @dp.message(Tests.type_of_test)
    async def get_type_of_test(message: types.Message, state: FSMContext):
        await state.update_data(type_of_tests=message.text)
        if message.text not in ["Рекомендованный", "Создам сам"]:
            await message.answer("Пожалуйста, выберите тип из предложенных")
            return
        if message.text == 'Рекомендованный':
            builder = InlineKeyboardBuilder()
            builder.row(
                InlineKeyboardButton(text="📚 Информация и Сообщения", callback_data="info_messages"),
                InlineKeyboardButton(text="🔢 Элементы теории алгоритмов", callback_data="algo_theory")
            )
            builder.row(
                InlineKeyboardButton(text="💬 Интерпретация дискретных сообщений", callback_data="discrete_messages"),
                InlineKeyboardButton(text="📊 Теорема Шеннона", callback_data="shannon_theorem")
            )
            await message.answer(
                "Выберите тему теста:",
                reply_markup=builder.as_markup()
            )
            await state.set_state(Tests.recommended_test)
        else:
            await message.answer('Выбери темы для вопросов')
            await state.set_state(Tests.topic)

    @dp.callback_query(Tests.recommended_test,
                       F.data.in_({"info_messages", "algo_theory", "discrete_messages", "shannon_theorem"}))
    async def choose_recommended_topic(callback: CallbackQuery, state: FSMContext):
        topic_map = {
            "info_messages": [180, 9],
            "algo_theory": [166, 59],
            "discrete_messages": [190, 64],
            "shannon_theorem": [255, 62]
        }

        topic_id, test_id = topic_map[callback.data]
        await state.update_data(topic_id=topic_id, test_id=test_id)

        await callback.answer()

        user = get_user_by_telegram(callback.from_user.username)
        data = await state.get_data()
        test_id = save_user_test(user['id'], "practice", 'fundamentals', 0, 0, data['topic_id'])

        update_questions(test_id, data['test_id'])
        questions = get_questions(test_id, user['id'])

        await state.update_data(test_id=test_id, cur_test=0, questions=questions)
        await state.set_state(Tests.execute_test)

        await callback.message.answer("Тест начался.")
        await callback.message.answer(questions[0]['question_text'])

    @dp.message(Tests.execute_test)
    async def execute_test(message: types.Message, state: FSMContext):
        data = await state.get_data()
        await state.update_data(cur_test=data['cur_test'] + 1)
        questions = data['questions']
        questions[data['cur_test']]['answer'] = message.text
        await state.update_data(questions=questions)
        if data['cur_test'] + 1 < 10:
            await state.update_data(cur_test=data['cur_test'] + 1)
            await message.answer(data['questions'][data['cur_test'] + 1]['question_text'])
            return
        print(data['questions'])
        await state.clear()
        await message.answer('Тест завершен')