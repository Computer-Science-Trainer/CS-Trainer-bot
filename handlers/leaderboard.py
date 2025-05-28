from aiogram import types
from aiogram import F
from aiogram.fsm.context import FSMContext
from httpx import HTTPStatusError
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from .api_client import api_get
from aiogram.fsm.state import State, StatesGroup
from messages.locale import messages

PAGE_SIZE = 10


class LeaderBoard(StatesGroup):
    quantity = State()
    topic = State()
    pagination = State()


def register_leaderboard(dp):
    @dp.message(Command("leaderboard"))
    async def getting_leaderboard(message: types.Message, state: FSMContext):
        topics_kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=messages["leaderboard"]
                                ["showAlgorithms"])],
                [KeyboardButton(text=messages["leaderboard"]
                                ["showFundamentals"])]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer(messages["leaderboard"]["chooseTopic"], reply_markup=topics_kb)
        await state.set_state(LeaderBoard.topic)

    @dp.message(LeaderBoard.topic)
    async def show_topic_leaderboard(
            message: types.Message, state: FSMContext):
        topics = [messages["leaderboard"]["showAlgorithms"],
                  messages["leaderboard"]["showFundamentals"]]
        if message.text not in topics:
            await message.answer(messages["leaderboard"]["invalidTopic"])
            return
        topic_key = 'algorithms' if message.text == topics[0] else 'fundamentals'
        await state.update_data(topic=topic_key)
        try:
            resp = await api_get('leaderboard')
            leaders = {
                'algorithms': resp.get('algorithms', []),
                'fundamentals': resp.get('fundamentals', [])
            }
        except HTTPStatusError:
            await message.answer(messages["leaderboard"]["loadError"], reply_markup=types.ReplyKeyboardRemove())
            await state.clear()
            return
        current_topic = topic_key
        await state.update_data(leaders=leaders, topic=current_topic, page=0)
        page_items = leaders[current_topic][0:PAGE_SIZE]
        total_pages = (len(leaders[current_topic]) - 1) // PAGE_SIZE + 1
        text = f"{messages['leaderboard']['chooseTopic']} '{message.text}' (страница 1/{total_pages}):\n"
        for idx, u in enumerate(page_items, start=1):
            text += f"{idx}. {u['username']} {u['score']}\n"
        builder = InlineKeyboardBuilder()
        if total_pages > 1:
            builder.button(text=messages["leaderboard"]["showNext"],
                           callback_data=f"lb_page:{current_topic}:1")
        other = 'fundamentals' if current_topic == 'algorithms' else 'algorithms'
        display_other = messages["leaderboard"]["showFundamentals"] if other == 'fundamentals' else messages["leaderboard"]["showAlgorithms"]
        builder.button(
            text=display_other,
            callback_data=f"lb_toggle:{other}")
        builder.adjust(2)
        await message.answer(text, reply_markup=builder.as_markup())
        await state.set_state(LeaderBoard.pagination)

    @dp.callback_query(LeaderBoard.pagination, F.data.startswith('lb_page:'))
    async def paginate(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        data = await state.get_data()
        leaders = data.get('leaders', {})
        _, topic_key, page_str = callback.data.split(':')
        page = int(page_str)
        items = leaders.get(topic_key, [])
        total_pages = (len(items) - 1) // PAGE_SIZE + 1
        start = page * PAGE_SIZE
        page_items = items[start:start + PAGE_SIZE]
        if topic_key == 'algorithms':
            topic_display = messages["leaderboard"]["showAlgorithms"]
        else:
            topic_display = messages["leaderboard"]["showFundamentals"]
        text = (
            f"{messages['leaderboard']['chooseTopic']} '"
            f"{topic_display}' (страница {page+1}/{total_pages}):\n"
        )
        for idx, u in enumerate(page_items, start=start + 1):
            text += f"{idx}. {u['username']} {u['score']}\n"
        builder = InlineKeyboardBuilder()
        if page > 0:
            builder.button(
                text=messages["leaderboard"]["showPrev"],
                callback_data=f"lb_page:{topic_key}:{page-1}"
            )
        if page < total_pages - 1:
            builder.button(
                text=messages["leaderboard"]["showNext"],
                callback_data=f"lb_page:{topic_key}:{page+1}"
            )
        other = 'fundamentals' if topic_key == 'algorithms' else 'algorithms'
        if other == 'fundamentals':
            display_other = messages["leaderboard"]["showFundamentals"]
        else:
            display_other = messages["leaderboard"]["showAlgorithms"]
        builder.button(
            text=display_other,
            callback_data=f"lb_toggle:{other}"
        )
        builder.adjust(2)
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await state.update_data(topic=topic_key, page=page)

    @dp.callback_query(LeaderBoard.pagination, F.data.startswith('lb_toggle:'))
    async def toggle_topic(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        data = await state.get_data()
        leaders = data.get('leaders', {})
        new_topic = callback.data.split(':')[1]
        items = leaders.get(new_topic, [])
        total_pages = (len(items) - 1) // PAGE_SIZE + 1
        page = 0
        start = 0
        page_items = items[start:start + PAGE_SIZE]
        if new_topic == 'algorithms':
            display_topic = messages["leaderboard"]["showAlgorithms"]
        else:
            display_topic = messages["leaderboard"]["showFundamentals"]
        text = (
            f"{messages['leaderboard']['chooseTopic']} '"
            f"{display_topic}' (страница 1/{total_pages}):\n"
        )
        for idx, u in enumerate(page_items, start=1):
            text += f"{idx}. {u['username']} {u['score']}\n"
        builder = InlineKeyboardBuilder()
        if total_pages > 1:
            builder.button(
                text=messages["leaderboard"]["showNext"],
                callback_data=f"lb_page:{new_topic}:1"
            )
        other = 'fundamentals' if new_topic == 'algorithms' else 'algorithms'
        if other == 'fundamentals':
            display_other = messages["leaderboard"]["showFundamentals"]
        else:
            display_other = messages["leaderboard"]["showAlgorithms"]
        builder.button(
            text=display_other,
            callback_data=f"lb_toggle:{other}"
        )
        builder.adjust(2)
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await state.update_data(topic=new_topic, page=page)
