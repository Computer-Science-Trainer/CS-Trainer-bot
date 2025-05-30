from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from httpx import HTTPStatusError
from .api_client import api_get, api_post
from aiogram.fsm.state import State, StatesGroup
from messages.locale import messages
from aiogram import Router


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
            [KeyboardButton(text="📝 Тесты")],
            [KeyboardButton(text="🏆 Таблица лидеров")],
            [KeyboardButton(text="👤 Обо мне")]
        ],
        resize_keyboard=True
    )


def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✨ Рекомендованные тесты",
        callback_data="choose_recommended")
    builder.button(text="📚 Все тесты", callback_data="choose_all")
    builder.adjust(1)
    return builder.as_markup()


def get_tests_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✨ Рекомендации")],
            [KeyboardButton(text="📚 Все тесты")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )


global_router = Router()


@global_router.message(F.text == "🔙 Назад")
async def handle_back(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🔙 <b>Вы вернулись в главное меню.</b>",
        reply_markup=get_main_reply_keyboard(),
        parse_mode="HTML"
    )
    return


def register_tests(dp):
    @dp.message(F.text == "✨ Рекомендации")
    async def show_recommended_tests(
            message: types.Message, state: FSMContext):
        username = message.from_user.username
        recs = await api_get(f"user/{username}/recommendations")
        builder = InlineKeyboardBuilder()
        for rec in recs:
            builder.button(
                text=f"🌟 {rec.replace('_', ' ').capitalize()}",
                callback_data=f"rec_{rec}"
            )
        builder.adjust(1)
        await message.answer(
            "<b>✨ Рекомендованные тесты:</b>",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        await state.set_state(Tests.recommended_test)

    @dp.message(F.text == "📚 Все тесты")
    async def show_all_tests(message: types.Message, state: FSMContext):
        await send_sections_keyboard(message, state)
        await state.set_state(Tests.topic)

    @dp.message(Tests.topic)
    async def handle_section_choice(message: types.Message, state: FSMContext):
        topics = (await state.get_data()).get('all_topics', [])
        section = None
        for t in topics:
            label = f"📖 {t.get('label', '').replace('_', ' ').capitalize()}"
            if label.lower() == message.text.strip().lower():
                section = t
                break
        if not section:
            await message.answer(
                "❗️ <b>Раздел не найден.</b>\nПожалуйста, выберите раздел из списка.",
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
            if isinstance(item, dict):
                topic_label = item.get(
                    'label', str(item)).replace(
                    '_', ' ').capitalize()
                lines.append(f"  {topic_number}. {topic_label}")
                all_topics_flat.append(([topic_number], topic_label))
                subtopics = item.get('accordions', [])
                sub_number = 1
                for j, sub in enumerate(subtopics, 1):
                    if isinstance(sub, dict):
                        sub_label = sub.get(
                            'label', str(sub)).replace(
                            '_', ' ').capitalize()
                        lines.append(
                            f"    {topic_number}.{sub_number}. {sub_label}")
                        all_topics_flat.append(
                            ([topic_number, sub_number], sub_label))
                        subsubtopics = sub.get('accordions', [])
                        subsub_number = 1
                        for k, subsub in enumerate(subsubtopics, 1):
                            subsub_label = str(subsub)
                            if isinstance(subsub, dict):
                                subsub_label = subsub.get('label', str(subsub))
                            subsub_label = subsub_label.replace(
                                '_', ' ').capitalize()
                            lines.append(
                                f"      {topic_number}.{sub_number}.{subsub_number}. {subsub_label}")
                            all_topics_flat.append(
                                ([topic_number, sub_number, subsub_number], subsub_label))
                            subsub_number += 1
                    else:
                        sub_label = str(sub).replace('_', ' ').capitalize()
                        lines.append(
                            f"    {topic_number}.{sub_number}. {sub_label}")
                        all_topics_flat.append(
                            ([topic_number, sub_number], sub_label))
                    sub_number += 1
                topic_number += 1
            else:
                topic_label = str(item).replace('_', ' ').capitalize()
                lines.append(f"  {topic_number}. {topic_label}")
                all_topics_flat.append(([topic_number], topic_label))
                topic_number += 1
        msg = f"<b>📖 Темы раздела:</b> <i>{section.get('label', '').replace('_', ' ').capitalize()}</i>\n\n" + "\n".join(
            lines)
        await message.answer(
            msg +
            "\n\n<em>Напишите номер темы, подтемы или подподтемы (например: 2.1.3)</em>",
            parse_mode="HTML"
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
                "❗️ Введите корректный номер темы, например: <b>2</b> или <b>1.2</b> или <b>1.2.3</b>",
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
                "❗️ Тема не найдена. Проверьте номер и попробуйте снова.",
                parse_mode="HTML"
            )
            return
        topic_id = label = found[1]
        await state.update_data(topic_id=topic_id)
        await message.answer(f"✅ <b>Вы выбрали тему:</b> <i>{label}</i>", parse_mode="HTML")
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
            user = await api_get(f"user/{name}", jwt_token=token)
            create_resp = await api_post('tests', {'section': 'FI', 'topics': [topic_id]}, token)
            test_id = create_resp.get('id') or create_resp.get('test_id')
            if not test_id:
                await send(messages["tests"]["errors"]["ErrorTitle"])
                await state.clear()
                return
            test_data = await api_get(f"tests/{test_id}", jwt_token=token)
            questions = test_data.get('questions')
        except HTTPStatusError:
            await send(messages["tests"]["errors"]["loadErrorDescription"])
            await state.clear()
            return
        await state.update_data(test_id=test_id, cur_test=0, questions=questions)
        await state.set_state(Tests.execute_test)
        # send first question in one inline message and store its identifiers
        builder = InlineKeyboardBuilder()
        opts = questions[0].get('options') or []
        for num, answer in enumerate(opts):
            builder.button(text=answer, callback_data=f"answer_{num}")
        builder.adjust(1)
        # nav row (only Next on first)
        if len(questions) > 1:
            builder.button(text="Next ▶️", callback_data="nav_next")
        builder.adjust(2)
        msg = await send(questions[0]['question_text'], reply_markup=builder.as_markup())
        await state.update_data(test_chat_id=msg.chat.id, test_message_id=msg.message_id)

    async def _show_question(callback_or_message, state: FSMContext, index: int):
        data = await state.get_data()
        questions = data['questions']
        question = questions[index]
        builder = InlineKeyboardBuilder()
        opts = question.get('options') or []
        for num, answer in enumerate(opts):
            builder.button(text=answer, callback_data=f"answer_{num}")
        builder.adjust(1)
        # nav row (Prev/Next)
        if index > 0:
            builder.button(text="◀️ Назад", callback_data="nav_prev")
        if index < len(questions) - 1:
            builder.button(text="Далее ▶️", callback_data="nav_next")
        builder.adjust(2)
        text = question.get('question_text', '')
        # edit the original test message
        chat_id = data['test_chat_id']
        message_id = data['test_message_id']
        await callback_or_message.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=builder.as_markup()
        )
        await state.update_data(cur_test=index)

    @dp.callback_query(Tests.recommended_test, F.data.startswith("rec_"))
    async def handle_recommended_topic(
            callback: types.CallbackQuery, state: FSMContext):
        topic = callback.data[4:]
        await state.update_data(topic_id=topic)
        await callback.message.answer(f"Вы выбрали тест: {topic.replace('_', ' ').capitalize()}")
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
            for num, answer in enumerate(question['options']):
                mark = '✅' if num in user_answer else '➕'
                builder.button(
                    text=f"{mark} {answer}",
                    callback_data=f"answer_{num}")
            builder.button(text="Ответить", callback_data="submit_multi")
            builder.adjust(1)
            await callback.message.edit_text(question['question_text'], reply_markup=builder.as_markup())
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
            for num, answer in enumerate(question['options']):
                mark = '✅' if num in user_answer else '◻️'
                builder.button(text=f"{mark} {answer}", callback_data=f"answer_{num}")
            if len(user_answer) == len(question['options']):
                builder.button(text="Ответить", callback_data="submit_ordering")
            builder.adjust(2)
            text = question['question_text']
            order = " → ".join(question['options'][i] for i in user_answer)
            await callback.message.edit_text(
                f"{text}\n\nВаш порядок: {order}",
                reply_markup=builder.as_markup()
            )
        else:
            selected_answer = question['options'][number_of_answer] if number_of_answer < len(question['options']) else ''
            question['user_answer'] = selected_answer
            questions[current_question_index] = question
            await state.update_data(questions=questions)
            next_idx = current_question_index + 1
            if next_idx < len(questions):
                await _show_question(callback, state, next_idx)
            else:
                await submit_test_results(callback.message, state)
        await callback.answer()

    @dp.callback_query(Tests.execute_test, F.data == "submit_multi")
    async def handle_multi_submit(
            callback: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        questions = data['questions']
        current_question_index = data['cur_test']
        question = questions[current_question_index]
        selected = question.get('user_answer', [])
        if selected:
            question['user_answer'] = [question['options'][i]
                                       for i in selected]
        else:
            question['user_answer'] = []
        questions[current_question_index] = question
        await state.update_data(questions=questions)
        await process_next_question(callback.message, state)

    @dp.callback_query(Tests.execute_test, F.data == "submit_ordering")
    async def handle_ordering_submit(
            callback: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        questions = data['questions']
        current_question_index = data['cur_test']
        question = questions[current_question_index]
        selected = question.get('user_answer', [])
        if selected:
            question['user_answer'] = [question['options'][i]
                                       for i in selected]
        else:
            question['user_answer'] = []
        questions[current_question_index] = question
        await state.update_data(questions=questions)
        await process_next_question(callback.message, state)

    async def process_next_question(message: types.Message, state: FSMContext):
        data = await state.get_data()
        questions = data['questions']
        next_idx = data['cur_test'] + 1
        if next_idx < len(questions):
            next_question = questions[next_idx]
            await state.update_data(cur_test=next_idx)
            if next_question.get('options') and next_question['options']:
                qtype = next_question.get('question_type', next_question.get('type', 'single'))
                if qtype == 'multiple':
                    user_answer = next_question.get('user_answer', [])
                    builder = InlineKeyboardBuilder()
                    for num, answer in enumerate(next_question['options']):
                        mark = '✅' if num in user_answer else '➕'
                        builder.button(
                            text=f"{mark} {answer}",
                            callback_data=f"answer_{num}")
                    builder.button(
                        text="Ответить",
                        callback_data="submit_multi")
                    builder.adjust(1)
                    await message.answer(next_question['question_text'], reply_markup=builder.as_markup())
                elif qtype == 'ordering':
                    user_answer = next_question.get('user_answer', [])
                    builder = InlineKeyboardBuilder()
                    order_text = "Ваш порядок: " + \
                        ' → '.join([next_question['options'][i]
                                   for i in user_answer]) if user_answer else ""
                    text = next_question['question_text']
                    if order_text:
                        text += f"\n\n{order_text}"
                    for num, answer in enumerate(next_question['options']):
                        if num not in user_answer:
                            builder.button(
                                text=answer, callback_data=f"answer_{num}")
                    if len(user_answer) == len(next_question['options']):
                        builder.button(
                            text="Ответить", callback_data="submit_ordering")
                    builder.adjust(1)
                    await message.answer(text, reply_markup=builder.as_markup())
                else:
                    # single-choice: inline-редактирование
                    await _show_question(message, state, next_idx)
            else:
                # Open-ended
                await _show_question(message, state, next_idx)
        else:
            await submit_test_results(message, state)

    async def submit_test_results(message: types.Message, state: FSMContext):
        data = await state.get_data()
        questions = data['questions']
        token = data.get('jwt_token')
        answers = []
        for q in questions:
            raw = q.get('user_answer')
            if isinstance(raw, list):
                answer_list = [str(item) for item in raw] if raw else [""]
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
                f"Разбор вашего теста доступен в Вашем профиле на сайте, войдя в личный кабинет: https://cs-trainer.netlify.app/{name}",
            )
        except HTTPStatusError:
            await message.answer(messages["tests"]["errors"]["loadErrorDescription"], reply_markup=get_main_reply_keyboard())
        await state.clear()

    @dp.message(Tests.execute_test,
                F.text.in_([messages["tests"]['moveNext'], messages["tests"]['moveBack']]))
    async def handle_move_buttons(message: types.Message, state: FSMContext):
        data = await state.get_data()
        questions = data['questions']
        current_question_index = data['cur_test']
        if message.text == messages["tests"]['moveNext']:
            if current_question_index + 1 < len(questions):
                await state.update_data(cur_test=current_question_index + 1)
                next_question = questions[current_question_index + 1]
                if next_question.get('options') and len(
                        next_question['options']) > 0:
                    builder = InlineKeyboardBuilder()
                    for num, answer in enumerate(next_question['options']):
                        builder.button(
                            text=answer, callback_data=f"answer_{num}")
                    builder.adjust(1)
                    await message.answer(next_question['question_text'], reply_markup=builder.as_markup())
                else:
                    await message.answer(next_question['question_text'])
            else:
                await message.answer(messages["tests"]["errors"].get("noNextQuestion", "Это последний вопрос."))
        elif message.text == messages["tests"]['moveBack']:
            if current_question_index > 0:
                await state.update_data(cur_test=current_question_index - 1)
                prev_question = questions[current_question_index - 1]
                if prev_question.get('options') and len(
                        prev_question['options']) > 0:
                    builder = InlineKeyboardBuilder()
                    for num, answer in enumerate(prev_question['options']):
                        builder.button(
                            text=answer, callback_data=f"answer_{num}")
                    builder.adjust(1)
                    await message.answer(prev_question['question_text'], reply_markup=builder.as_markup())
                else:
                    await message.answer(prev_question['question_text'])
            else:
                await message.answer(messages["tests"]["errors"].get("noPrevQuestion", "Это первый вопрос."))

    # вместо process_next_question для текстового ответа
    @dp.message(Tests.execute_test)
    async def handle_text_answer(message: types.Message, state: FSMContext):
        data = await state.get_data()
        questions = data['questions']
        idx = data['cur_test']
        questions[idx]['user_answer'] = message.text
        await state.update_data(questions=questions)
        # переходим к следующему вопросу через редактирование
        await _show_question(message, state, idx + 1)

    @dp.callback_query(Tests.topic, F.data.startswith("topic_"))
    async def handle_topic_choice(
            callback: types.CallbackQuery, state: FSMContext):
        topic_label = callback.data[6:]
        await state.update_data(topic_id=topic_label)
        await callback.message.answer(f"Вы выбрали тему: {topic_label.replace('_', ' ').capitalize()}")
        await start_test_by_topic(callback, state, topic_label)
        await callback.answer()

    async def send_sections_keyboard(
            message: types.Message, state: FSMContext):
        try:
            topics = await api_get("topics")
        except Exception:
            await message.answer(
                "❌ <b>Ошибка получения списка всех тестов.</b>",
                reply_markup=get_main_reply_keyboard(),
                parse_mode="HTML"
            )
            return
        await state.update_data(all_topics=topics)
        section_buttons = [
            KeyboardButton(
                text=f"📖 {sec.get('label','').replace('_',' ').capitalize()}") for sec in topics]
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [btn] for btn in section_buttons],
            resize_keyboard=True,
            one_time_keyboard=True)
        await message.answer(
            "<b>Выберите раздел:</b>",
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
