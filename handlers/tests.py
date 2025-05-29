from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.command import Command
from httpx import HTTPStatusError
from .api_client import api_get, api_post
from aiogram.fsm.state import State, StatesGroup
from messages.locale import messages


class Tests(StatesGroup):
    type_of_test = State()
    total_topic = State()
    recommended_test = State()
    topic = State()
    start_test = State()
    execute_test = State()
    end_test = State()


def register_tests(dp):
    @dp.message(Command("tests"))
    async def getting_leaderboard(message: types.Message, state: FSMContext):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text='Поехали!', callback_data='start_test'))
        await message.answer(
            messages["main"]["commands"]["tests"],
            reply_markup=builder.as_markup()
        )
        await state.set_state(Tests.type_of_test)

    @dp.callback_query(Tests.type_of_test, F.data == "start_test")
    async def get_type_of_test(callback: types.CallbackQuery, state: FSMContext):
        await state.update_data(type_of_tests='start_test')
        data = await state.get_data()
        test_type = data.get("type_of_tests")
        valid_types = [
            'start_test',
            "Создам сам"
        ]
        if test_type not in valid_types:
            await callback.message.answer(messages["leaderboard"]["invalidTopic"])
            return

        if test_type == 'start_test':
            builder = InlineKeyboardBuilder()
            builder.row(
                types.InlineKeyboardButton(
                    text="📚 Информация и Сообщения",
                    callback_data="info_messages"),
                types.InlineKeyboardButton(
                    text="🔢 Элементы теории алгоритмов",
                    callback_data="algo_theory")
            )
            builder.row(
                types.InlineKeyboardButton(
                    text="💬 Интерпретация дискретных сообщений",
                    callback_data="discrete_messages"),
                types.InlineKeyboardButton(
                    text="📊 Теорема Шеннона",
                    callback_data="shannon_theorem")
            )
            await callback.message.answer(
                messages["tests"]["chooseTopic"],
                reply_markup=builder.as_markup()
            )
            await state.set_state(Tests.recommended_test)
        else:
            await callback.message.answer(messages["leaderboard"]["chooseTopic"])
            await state.set_state(Tests.topic)
        await callback.answer()

    @dp.callback_query(Tests.recommended_test,
                       F.data.in_({"info_messages", "algo_theory", "discrete_messages", "shannon_theorem"}))
    async def choose_recommended_topic(
            callback: CallbackQuery, state: FSMContext):
        topic_map = {
            "info_messages": [180, 9],
            "algo_theory": [166, 59],
            "discrete_messages": [190, 64],
            "shannon_theorem": [255, 62]
        }

        topic_id, test_id = topic_map[callback.data]
        await state.update_data(topic_id=topic_id, test_id=test_id)

        await callback.answer()
        data = await state.get_data()
        token = data.get('jwt_token')
        username = callback.from_user.username
        try:
            login = await api_post('auth/login-telegram', {'telegram_username': username})
            name = login.get('username', username)
            user = await api_get(f"user/{name}", jwt_token=token)
            create_resp = await api_post('tests', {'section': 'FI', 'topics': [callback.data]}, token)
            test_id = create_resp.get('id') or create_resp.get('test_id')
            if not test_id:
                await callback.message.answer(messages["tests"]["errors"]["ErrorTitle"])
                await state.clear()
                return
            test_data = await api_get(f"tests/{test_id}", jwt_token=token)
            questions = test_data.get('questions', [])
        except HTTPStatusError:
            await callback.message.answer(messages["tests"]["errors"]["loadErrorDescription"])
            await state.clear()
            return

        await state.update_data(test_id=test_id, cur_test=0, questions=questions)
        await state.set_state(Tests.execute_test)

        await callback.message.answer(messages["tests"]["started"])
        await callback.message.answer(questions[0]['question_text'])

    @dp.message(Tests.execute_test)
    async def execute_test(message: types.Message, state: FSMContext):
        data = await state.get_data()
        token = data.get('jwt_token')
        questions = data['questions']
        questions[data['cur_test']]['user_answer'] = message.text
        await state.update_data(questions=questions)
        cur = data['cur_test']
        if cur + 1 < len(questions):
            await state.update_data(cur_test=cur + 1)
            await message.answer(questions[cur + 1]['question_text'])
            return
        answers = [{'question_id': q['id'], 'answer': q['user_answer']}
                   for q in questions]
        try:
            result = await api_post(f"tests/{data['test_id']}/submit", {'answers': answers}, token)
            message_data = {
                'passed': result['passed'],
                'accuracy': round(result['passed'] / result['total'] * 100),
                'earned_score': result['earned_score']
            }
            await message.answer(messages["tests"]["completed"].format(**message_data))
        except HTTPStatusError:
            await message.answer(messages["tests"]["errors"]["loadErrorDescription"])
        await state.clear()
