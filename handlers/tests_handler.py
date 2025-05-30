from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from httpx import HTTPStatusError
from .api_client import api_get, api_post
from aiogram.fsm.state import State, StatesGroup
from messages.locale import messages
from aiogram import Router
import datetime


class Tests(StatesGroup):
    type_of_test = State()
    total_topic = State()
    recommended_test = State()
    topic = State()
    start_test = State()
    execute_test = State()
    end_test = State()


def get_main_reply_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=messages["main"]["menuTests"])],
            [KeyboardButton(text=messages["main"]["menuLeaderboard"])],
            [KeyboardButton(text=messages["main"]["menuMe"])]
        ],
        resize_keyboard=True
    )


def get_tests_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=messages["tests"]["menuRecommendations"])],
            [KeyboardButton(text=messages["tests"]["menuAllTests"])],
            [KeyboardButton(text=messages["main"]["back"])]],
        resize_keyboard=True
    )


def get_finish_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=messages["tests"]["finishTest"])]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


global_router = Router()


@global_router.message(lambda m: m.text and m.text.strip()
                       == messages["main"]["back"])
async def handle_back(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        messages["main"]["backToMain"],
        reply_markup=get_main_reply_keyboard(),
        parse_mode="HTML"
    )
    return


def get_remaining_time(end_time_str):
    end = datetime.datetime.fromisoformat(end_time_str)
    now = datetime.datetime.now()
    delta = end - now
    total = int(delta.total_seconds())
    if total <= 0:
        return "00:00"
    m, s = divmod(total, 60)
    h, m = divmod(m, 60)
    if h:
        return messages["tests"]["timeHMS"].format(h=h, m=m, s=s)
    elif m:
        return messages["tests"]["timeMS"].format(m=m, s=s)
    else:
        return messages["tests"]["timeS"].format(s=s)


def register_tests(dp):
    @dp.message(F.text == messages["tests"]["menuRecommendations"])
    async def show_recommended_tests(
            message: types.Message, state: FSMContext):
        data = await state.get_data()
        username = data.get('site_username')
        if not username:
            tg_username = message.from_user.username
            login = await api_post('auth/login-telegram', {'telegram_username': tg_username})
            username = login.get('username', tg_username)
            await state.update_data(site_username=username)
        recs = await api_get(f"user/{username}/recommendations")
        lines = []
        builder = InlineKeyboardBuilder()
        for idx, rec in enumerate(recs, start=1):
            label = messages["tests"]["topics"][rec]
            lines.append(f"{idx}. {label}")
            builder.button(text=str(idx), callback_data=f"rec_{rec}")
        builder.adjust(6)
        text = messages["tests"]["recommended"] + "\n\n" + "\n".join(lines)
        await message.answer(
            text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        await state.set_state(Tests.recommended_test)

    @dp.message(F.text == messages["tests"]["menuAllTests"])
    async def show_all_tests(message: types.Message, state: FSMContext):
        await send_sections_keyboard(message, state)
        await state.set_state(Tests.topic)

    @dp.message(Tests.topic)
    async def handle_section_choice(message: types.Message, state: FSMContext):
        topics = (await state.get_data()).get('all_topics', [])
        section = None
        for t in topics:
            label = f"📖 {messages['tests']['sections'][t.get('label')]}"
            if label.lower() == message.text.strip().lower():
                section = t
                break
        if not section:
            await message.answer(
                messages["tests"]["sectionNotFound"],
                reply_markup=get_main_reply_keyboard(),
                parse_mode="HTML"
            )
            return

        def count_topics(section):
            count = 0
            for item in section.get('accordions', []):
                count += 1
            return count
        section_idx = topics.index(section)
        offset = sum(count_topics(topics[i]) for i in range(section_idx))
        all_topics_flat = []
        lines = []
        topic_number = offset + 1
        for i, item in enumerate(section.get('accordions', []), 1):
            item_key = item.get('label', str(item))
            topic_label = messages["tests"]["topics"][item_key]
            lines.append(f"  {topic_label}")
            all_topics_flat.append(([topic_number], topic_label))
            subtopics = item.get('accordions', [])
            sub_number = 1
            for j, sub in enumerate(subtopics, 1):
                if isinstance(sub, dict):
                    sub_label = messages["tests"]["topics"][sub.get('label')]
                    lines.append(
                        f"    {sub_label}")
                    all_topics_flat.append(
                        ([topic_number, sub_number], sub_label))
                    subsubtopics = sub.get('accordions', [])
                    subsub_number = 1
                    for k, subsub in enumerate(subsubtopics, 1):
                        if isinstance(subsub, dict):
                            subsub_label = messages["tests"]["topics"][subsub['label']]
                        else:
                            subsub_label = messages["tests"]["topics"][subsub]
                        lines.append(
                            f"      {subsub_label}")
                        all_topics_flat.append(
                            ([topic_number, sub_number, subsub_number], subsub_label))
                        subsub_number += 1
                else:
                    sub_label = messages["tests"]["topics"][sub]
                    lines.append(
                        f"    {sub_label}")
                    all_topics_flat.append(
                        ([topic_number, sub_number], sub_label))
                sub_number += 1
            topic_number += 1
        msg = messages["tests"]["sectionTopics"].format(section=messages['tests']['sections'][section['label']]) + \
            "\n\n" + "\n".join(lines)
        await message.answer(
            msg + "\n\n" + messages["tests"]["writeTopicNumber"],
            parse_mode="HTML",
            reply_markup=get_tests_menu_keyboard()
        )
        await state.update_data(current_section=section, all_topics_flat=all_topics_flat)
        await state.set_state(Tests.total_topic)

    @dp.message(Tests.total_topic)
    async def handle_topic_number(message: types.Message, state: FSMContext):
        all_topics_flat = (await state.get_data()).get('all_topics_flat')
        user_input = message.text.strip()
        parts = user_input.split('.')
        try:
            parts = [int(p) for p in parts]
        except ValueError:
            await message.answer(
                messages["tests"]["enterCorrectTopicNumber"],
                parse_mode="HTML"
            )
            return
        found = None
        for nums, label in all_topics_flat:
            if nums == parts:
                found = (nums, label)
                break
        if not found:
            await message.answer(
                messages["tests"]["topicNotFound"],
                parse_mode="HTML"
            )
            return
        topic_id = label = found[1]
        await state.update_data(topic_id=topic_id)
        await message.answer(
            messages["tests"]["topicChosen"].format(label=label),
            reply_markup=get_finish_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(Tests.start_test)

    @dp.message(Tests.start_test, F.text == messages["tests"]["finishTest"])
    async def start_test_on_finish(message: types.Message, state: FSMContext):
        data = await state.get_data()
        topic_id = data.get('topic_id')
        await start_test_by_topic(message, state, topic_id)

    async def start_test_by_topic(callback_or_message, state, topic_id):
        data = await state.get_data()
        token = data.get('jwt_token')
        is_callback = hasattr(callback_or_message, "message")
        if is_callback:
            user_obj = callback_or_message.from_user
            send = callback_or_message.message.answer
        else:
            user_obj = callback_or_message.from_user
            send = callback_or_message.answer
        username = user_obj.username
        if not token:
            try:
                resp = await api_post('auth/check-telegram', {'telegram_username': username})
                if resp.get('exists'):
                    login = await api_post('auth/login-telegram', {'telegram_username': username})
                    token = login.get('access_token') or login.get('token')
                    if token:
                        await state.update_data(jwt_token=token)
                    else:
                        await send(messages["registration"]["tokenError"])
                        await state.clear()
                        return
                else:
                    await send(messages["registration"]["needUsername"])
                    await state.clear()
                    return
            except HTTPStatusError:
                await send(messages["registration"]["connectionError"])
                return
        try:
            login = await api_post('auth/login-telegram', {'telegram_username': username})
            name = login.get('username', username)
            await state.update_data(site_username=name)
            create_resp = await api_post('tests', {'section': 'FI', 'topics': [topic_id]}, token)
            test_id = create_resp.get('id') or create_resp.get('test_id')
            if not test_id:
                await send(messages["tests"]["errors"]["ErrorTitle"])
                await state.clear()
                return
            test_data = await api_get(f"tests/{test_id}", jwt_token=token)
            questions = test_data.get('questions')
            end_time = test_data.get('end_time')
            await state.update_data(end_time=end_time)
        except HTTPStatusError:
            await send(messages["tests"]["errors"]["loadErrorDescription"])
            await state.clear()
            return
        await state.update_data(test_id=test_id, cur_test=0, questions=questions)
        await state.set_state(Tests.execute_test)
        opts = questions[0].get('options') or []
        options_text = "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(opts))
        qt = questions[0]['question_text'].strip()
        ot = options_text.strip()
        if ot:
            full_text = (
                f"<b>{messages['tests']['question']} 1</b>\n\n"
                f"{qt}\n\n"
                f"{ot}\n\n"
                f"⏰ {messages['tests']['remainingTime']}: "
                f"{get_remaining_time(end_time)}"
            )
        else:
            full_text = (
                f"<b>{messages['tests']['question']} 1</b>\n\n"
                f"{qt}\n\n"
                f"⏰ {messages['tests']['remainingTime']}: "
                f"{get_remaining_time(end_time)}"
            )
        builder = InlineKeyboardBuilder()
        for i in range(len(opts)):
            builder.button(text=str(i + 1), callback_data=f"answer_{i}")
        builder.adjust(1)
        if len(questions) > 1:
            builder.button(
                text=messages["tests"]["navNext"],
                callback_data="nav_next")
        builder.adjust(2)
        msg = await send(full_text, reply_markup=builder.as_markup(), parse_mode="HTML")
        await state.update_data(test_chat_id=msg.chat.id, test_message_id=msg.message_id)

    async def _show_question(
            callback_or_message, state: FSMContext, index: int):
        data = await state.get_data()
        if index == 10:
            chat_id = data['test_chat_id']
            message_id = data['test_message_id']
            finish_text = messages["tests"]["finish10Prompt"]
            await state.update_data(cur_test=index)
            builder = InlineKeyboardBuilder()
            builder.button(
                text=messages["tests"]["navPrev"],
                callback_data="nav_prev"
            )
            builder.adjust(1)
            await callback_or_message.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=finish_text,
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
            return

        question = data['questions'][index]
        opts = question.get('options') or []
        options_text = "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(opts))
        qt = question.get('question_text', '')
        ot = options_text
        if ot:
            full_text = (
                f"<b>{messages['tests']['question']} {index+1}</b>\n\n"
                f"{qt}\n\n"
                f"{ot}\n\n"
                f"⏰ {messages['tests']['remainingTime']}: "
                f"{get_remaining_time(data.get('end_time'))}"
            )
        else:
            full_text = (
                f"<b>{messages['tests']['question']} {index+1}</b>\n\n"
                f"{qt}\n\n"
                f"⏰ {messages['tests']['remainingTime']}: "
                f"{get_remaining_time(data.get('end_time'))}"
            )
        builder = InlineKeyboardBuilder()
        for i in range(len(opts)):
            builder.button(text=str(i + 1), callback_data=f"answer_{i}")
        if index > 0:
            builder.button(
                text=messages["tests"]["navPrev"],
                callback_data="nav_prev")
        if index < len(data['questions']):
            builder.button(
                text=messages["tests"]["navNext"],
                callback_data="nav_next")
        builder.adjust(2)
        await callback_or_message.bot.edit_message_text(
            chat_id=data['test_chat_id'],
            message_id=data['test_message_id'],
            text=full_text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        await state.update_data(cur_test=index)

    @dp.callback_query(Tests.recommended_test, F.data.startswith("rec_"))
    async def handle_recommended_topic(
            callback: types.CallbackQuery, state: FSMContext):
        topic = callback.data[4:]
        label = messages["tests"]["topics"][topic]
        await callback.message.answer(
            messages["tests"]["recommendedTopicChosen"].format(label=label),
            reply_markup=get_finish_keyboard()
        )
        await start_test_by_topic(callback, state, topic)
        await callback.answer()

    @dp.callback_query(Tests.execute_test, F.data.startswith("answer_"))
    async def handle_answer_selection(
            callback: types.CallbackQuery, state: FSMContext):
        number_of_answer = int(callback.data.split("answer_")[1])
        data = await state.get_data()
        questions = data['questions']
        current_question_index = data['cur_test']
        question = questions[current_question_index]
        qtype = question.get('question_type')
        if qtype == 'multiple-choice':
            user_answer = question.get('user_answer', [])
            if number_of_answer in user_answer:
                user_answer.remove(number_of_answer)
            else:
                user_answer.append(number_of_answer)
            question['user_answer'] = user_answer
            questions[current_question_index] = question
            await state.update_data(questions=questions)
            builder = InlineKeyboardBuilder()
            for num in range(len(question['options'])):
                mark = '✅' if num in user_answer else '➕'
                builder.button(
                    text=f"{mark} {num+1}",
                    callback_data=f"answer_{num}")
            builder.button(
                text=messages["tests"]["submitMulti"],
                callback_data="submit_multi")
            builder.adjust(1)
            builder.adjust(1)
            opts = question.get('options') or []
            options_text = "\n".join(
                f"{i+1}. {opt}" for i,
                opt in enumerate(opts))
            qt = question['question_text']
            ot = options_text
            if ot:
                full_text = (
                    f"<b>{messages['tests']['question']} {current_question_index+1}</b>\n\n"
                    f"{qt}\n\n"
                    f"{ot}\n\n"
                    f"⏰ {messages['tests']['remainingTime']}: "
                    f"{get_remaining_time(data.get('end_time'))}"
                )
            else:
                full_text = (
                    f"<b>{messages['tests']['question']} {current_question_index+1}</b>\n\n"
                    f"{qt}\n\n"
                    f"⏰ {messages['tests']['remainingTime']}: "
                    f"{get_remaining_time(data.get('end_time'))}"
                )
            await callback.message.edit_text(full_text, reply_markup=builder.as_markup(), parse_mode="HTML")
        elif qtype == 'ordering':
            user_answer = question.get('user_answer', [])
            if number_of_answer in user_answer:
                user_answer.remove(number_of_answer)
            else:
                user_answer.append(number_of_answer)
            question['user_answer'] = user_answer
            questions[current_question_index] = question
            await state.update_data(questions=questions)
            builder = InlineKeyboardBuilder()
            for num in range(len(question['options'])):
                mark = '✅' if num in user_answer else '◻️'
                builder.button(
                    text=f"{mark} {num+1}",
                    callback_data=f"answer_{num}")
            if len(user_answer) == len(question['options']):
                builder.button(
                    text=messages["tests"]["submitOrdering"],
                    callback_data="submit_ordering")
            builder.adjust(2)
            text = question['question_text']
            order = " → ".join(str(i + 1) for i in user_answer)
            opts = question.get('options') or []
            options_text = "\n".join(
                f"{i+1}. {opt}" for i,
                opt in enumerate(opts))
            qt = text
            ot = options_text
            if ot:
                full_text = (
                    f"<b>{messages['tests']['question']} {current_question_index+1}</b>\n\n"
                    f"{qt}\n\n"
                    f"{ot}\n\n"
                    f"{messages['tests']['yourOrder']} {order}\n\n"
                    f"⏰ {messages['tests']['remainingTime']}: "
                    f"{get_remaining_time(data.get('end_time'))}"
                )
            else:
                full_text = (
                    f"<b>{messages['tests']['question']} {current_question_index+1}</b>\n\n"
                    f"{qt}\n\n"
                    f"{messages['tests']['yourOrder']} {order}\n\n"
                    f"⏰ {messages['tests']['remainingTime']}: "
                    f"{get_remaining_time(data.get('end_time'))}"
                )
            await callback.message.edit_text(full_text, reply_markup=builder.as_markup(), parse_mode="HTML")
        else:
            selected_answer = question['options'][number_of_answer] \
                if number_of_answer < len(question['options']) else ''
            question['user_answer'] = selected_answer
            questions[current_question_index] = question
            await state.update_data(questions=questions)
            next_idx = current_question_index + 1
            if next_idx <= len(questions):
                await _show_question(callback, state, next_idx)
        await callback.answer()

    @dp.callback_query(Tests.execute_test, F.data == "submit_multi")
    async def handle_multi_submit(
            callback: types.CallbackQuery, state: FSMContext):
        await process_next_question(callback.message, state)

    @dp.callback_query(Tests.execute_test, F.data == "submit_ordering")
    async def handle_ordering_submit(
            callback: types.CallbackQuery, state: FSMContext):
        await process_next_question(callback.message, state)

    @dp.message(Tests.execute_test, F.text == messages["tests"]["finishTest"])
    async def handle_finish_via_markup(
            message: types.Message, state: FSMContext):
        await submit_test_results(message, state)

    async def process_next_question(message: types.Message, state: FSMContext):
        data = await state.get_data()
        questions = data['questions']
        next_idx = data['cur_test'] + 1
        if next_idx <= len(questions):
            await state.update_data(cur_test=next_idx)
            await _show_question(message, state, next_idx)

    async def submit_test_results(message: types.Message, state: FSMContext):
        data = await state.get_data()
        questions = data['questions']
        token = data.get('jwt_token')
        answers = []
        for q in questions:
            raw = q.get('user_answer')
            opts = q.get('options', [])
            if isinstance(raw, list):
                mapped = []
                for item in raw:
                    if isinstance(item, int) and item < len(opts):
                        mapped.append(opts[item])
                    elif isinstance(item, str):
                        mapped.append(item)
                answer_list = mapped or [""]
            elif raw is not None:
                answer_list = [str(raw)]
            else:
                answer_list = [""]
            answers.append({
                'question_id': int(q['id']),
                'answer': answer_list
            })
        try:
            result = await api_post(f"tests/{data['test_id']}/submit",
                                    {'answers': answers},
                                    token)
            message_data = {
                'passed': result['passed'],
                'accuracy': round(result['passed'] / result['total'] * 100),
                'earned_score': result['earned_score']
            }
            await message.answer(
                messages["tests"]["completed"].format(**message_data),
                reply_markup=get_main_reply_keyboard()
            )
            name = data.get('site_username')
            await message.answer(
                messages["tests"]["testReview"].format(name=name),
            )
        except HTTPStatusError:
            await message.answer(messages["tests"]["errors"]["loadErrorDescription"],
                                 reply_markup=get_main_reply_keyboard())
        await state.clear()

    @dp.message(Tests.execute_test)
    async def handle_text_answer(message: types.Message, state: FSMContext):
        data = await state.get_data()
        questions = data['questions']
        idx = data['cur_test']
        questions[idx]['user_answer'] = message.text
        await state.update_data(questions=questions)
        next_idx = idx + 1
        if next_idx <= len(questions):
            await _show_question(message, state, next_idx)

    @dp.callback_query(Tests.topic, F.data.startswith("topic_"))
    async def handle_topic_choice(
            callback: types.CallbackQuery, state: FSMContext):
        topic_label = callback.data[6:]
        label = messages["tests"]["topics"][topic_label]
        await callback.message.answer(messages["tests"]["topicChosenShort"].format(label=label))
        await start_test_by_topic(callback, state, topic_label)
        await callback.answer()

    async def send_sections_keyboard(
            message: types.Message, state: FSMContext):
        try:
            topics = await api_get("topics")
        except Exception:
            await message.answer(
                messages["tests"]["allTestsLoadError"],
                reply_markup=get_main_reply_keyboard(),
                parse_mode="HTML"
            )
            return
        await state.update_data(all_topics=topics)
        section_buttons = []
        for sec in topics:
            sec_label = messages["tests"]["sections"][sec['label']]
            section_buttons.append(KeyboardButton(text=f"📖 {sec_label}"))
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [btn] for btn in section_buttons],
            resize_keyboard=True,
            one_time_keyboard=True)
        await message.answer(
            messages["tests"]["chooseSection"],
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    @dp.callback_query(Tests.execute_test, F.data == "nav_prev")
    async def on_nav_prev(callback: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        idx = data['cur_test'] - 1
        await _show_question(callback, state, idx)
        await callback.answer()

    @dp.callback_query(Tests.execute_test, F.data == "nav_next")
    async def on_nav_next(callback: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        idx = data['cur_test'] + 1
        await _show_question(callback, state, idx)
        await callback.answer()
