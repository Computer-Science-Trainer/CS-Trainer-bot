from aiogram import types
from aiogram import F
from aiogram.fsm.context import FSMContext
from httpx import HTTPStatusError
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from .api_client import api_get
from aiogram.fsm.state import State, StatesGroup
from messages.locale import messages

PAGE_SIZE = 10


class LeaderBoard(StatesGroup):
    quantity = State()
    topic = State()
    pagination = State()


def get_topics_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(
                text=f"⚙️ {messages['leaderboard']['showFundamentals']}")],
            [KeyboardButton(
                text=f"🧮 {messages['leaderboard']['showAlgorithms']}")],
            [KeyboardButton(text=messages["main"]["back"])]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def generate_leaderboard_page(leaders: dict, topic_key: str, page: int):
    items = leaders.get(topic_key, [])
    total_pages = (len(items) - 1) // PAGE_SIZE + 1
    start = page * PAGE_SIZE
    page_items = items[start:start + PAGE_SIZE]
    if topic_key == 'algorithms':
        display_topic = messages['tests']['sections']['algorithms']
        topic_emoji = "🧮"
    else:
        display_topic = messages['tests']['sections']['fundamentals']
        topic_emoji = "⚙️"
    text = f"<b>{topic_emoji} {messages['leaderboard']['showing']}: {display_topic}</b> <i>({messages['leaderboard']['pageShort']} {page+1}/{total_pages})</i>\n\n"
    medals = ['🥇', '🥈', '🥉']
    for idx, u in enumerate(page_items, start=1):
        if page == 0 and idx <= 3:
            medal = medals[idx - 1]
        else:
            medal = f"<b>{start + idx}.</b>"
        text += f"{medal} <b>{u['username']}</b> — <code>{u['score']}</code>\n"

    builder = InlineKeyboardBuilder()
    if page > 0:
        builder.button(text=f"⬅️ {messages['leaderboard']['showPrev']}",
                       callback_data=f"lb_page:{topic_key}:{page-1}")
    if page < total_pages - 1:
        builder.button(text=f"{messages['leaderboard']['showNext']} ➡️",
                       callback_data=f"lb_page:{topic_key}:{page+1}")
    builder.adjust(2)

    return text, builder, total_pages


def register_leaderboard(dp):
    @dp.message(lambda m: m.text and m.text.strip() == messages["main"]["menuLeaderboard"])
    async def leaderboard_entrypoint(
            message: types.Message, state: FSMContext):
        await state.set_state(LeaderBoard.topic)
        await message.answer(
            messages["leaderboard"]["chooseTopicView"],
            reply_markup=get_topics_keyboard(),
            parse_mode="HTML"
        )

    @dp.message(LeaderBoard.topic)
    async def show_topic_leaderboard(
            message: types.Message, state: FSMContext):
        topics = [f"🧮 {messages['leaderboard']['showAlgorithms']}",
                  f"⚙️ {messages['leaderboard']['showFundamentals']}"]
        if message.text not in topics:
            await message.answer(
                f"❗️ <b>{messages['leaderboard']['invalidTopic']}</b>",
                reply_markup=get_topics_keyboard(),
                parse_mode="HTML"
            )
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
            await message.answer(
                f"❌ <b>{messages['leaderboard']['loadError']}</b>",
                reply_markup=types.ReplyKeyboardRemove(),
                parse_mode="HTML"
            )
            await state.clear()
            return
        current_topic = topic_key
        await state.update_data(leaders=leaders, topic=current_topic, page=0)

        text, builder, total_pages = generate_leaderboard_page(
            leaders, current_topic, 0)

        if topic_key == 'algorithms':
            display_other = f"⚙️ {messages['leaderboard']['showFundamentals']}"
        else:
            display_other = f"🧮 {messages['leaderboard']['showAlgorithms']}"
        reply_kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=display_other)],
                [KeyboardButton(text=messages["main"]["back"])]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        await message.answer(
            messages["leaderboard"]["changeTopicHint"],
            reply_markup=reply_kb,
            parse_mode="HTML"
        )
        await state.set_state(LeaderBoard.pagination)

    @dp.message(LeaderBoard.pagination)
    async def handle_topic_switch_keyboard(
            message: types.Message, state: FSMContext):
        data = await state.get_data()
        if message.text == f"🧮 {messages['leaderboard']['showAlgorithms']}":
            new_topic = 'algorithms'
        elif message.text == f"⚙️ {messages['leaderboard']['showFundamentals']}":
            new_topic = 'fundamentals'
        elif message.text == messages["main"]["back"]:
            from handlers.tests import get_main_reply_keyboard
            await state.clear()
            await message.answer(messages["main"]["backToMain"], reply_markup=get_main_reply_keyboard())
            return
        else:
            await message.answer(f"❗️ <b>{messages['leaderboard']['invalidTopic']}</b>", parse_mode="HTML")
            return
        leaders = data.get('leaders', {})
        items = leaders.get(new_topic, [])
        total_pages = (len(items) - 1) // PAGE_SIZE + 1
        page = 0
        start = 0
        page_items = items[start:start + PAGE_SIZE]
        if new_topic == 'algorithms':
            display_topic = f"{messages['tests']['sections']['algorithms']}"
            display_other = f"⚙️ {messages['leaderboard']['showFundamentals']}"
            topic_emoji = "🧮"
        else:
            display_topic = f"{messages['tests']['sections']['fundamentals']}"
            display_other = f"🧮 {messages['leaderboard']['showAlgorithms']}"
            topic_emoji = "⚙️"
        text = (
            f"<b>{topic_emoji} {messages['leaderboard']['showing']}: "
            f"{display_topic}</b> <i>({messages['leaderboard']['pageShort']} 1/{total_pages})</i>\n\n"
        )
        medals = ['🥇', '🥈', '🥉']
        for idx, u in enumerate(page_items, start=1):
            medal = medals[idx - 1] if idx <= 3 else f"<b>{idx}.</b>"
            text += f"{medal} <b>{u['username']}</b> — <code>{u['score']}</code>\n"
        builder = InlineKeyboardBuilder()
        if total_pages > 1:
            builder.button(
                text=f"{messages['leaderboard']['showNext']} ➡️",
                callback_data=f"lb_page:{new_topic}:1"
            )
        builder.adjust(1)
        reply_kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=display_other)],
                [KeyboardButton(text=messages["main"]["back"])]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        await message.answer(
            messages["leaderboard"]["changeTopicHint"],
            reply_markup=reply_kb,
            parse_mode="HTML"
        )
        await state.update_data(topic=new_topic, page=0)

    @dp.callback_query(LeaderBoard.pagination, F.data.startswith('lb_page:'))
    async def paginate(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        data = await state.get_data()
        leaders = data.get('leaders', {})
        _, topic_key, page_str = callback.data.split(':')
        page = int(page_str)

        text, builder, total_pages = generate_leaderboard_page(
            leaders, topic_key, page)
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        await state.update_data(topic=topic_key, page=page)
