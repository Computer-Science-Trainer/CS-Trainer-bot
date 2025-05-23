from aiogram import types
from aiogram import F
import random
from logging import error
# from aiogram.filters import Text
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from services.user_service import save_user, change_db_users, get_user_by_email
from stations import Registration
from security import create_access_token, decode_access_token, verify_password
from services.email_service import send_verification_email

MAX_AVATAR_SIZE = 1024 * 300  # 300 KB
MAX_USERNAME_LEN = 32
MAX_EMAIL_LEN = 320
MAX_TELEGRAM_LEN = 255
MAX_GITHUB_LEN = 255
MAX_WEBSITE_LEN = 255
MAX_BIO_LEN = 500


def generate_verification_code() -> str:
    return f"{random.randint(0, 999999):06d}"


def register_handlers(dp):
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message, state: FSMContext):
        text = ('Привет! Тебе нужна помощь в подготовке к Зайцеву?\nТы по адресу! '
                'Но для начала, давай проверим твою регистрацию.\n'
                '(Даже если ее нет, просто следуй инструкции.) \n Введи свою почту:')
        remove_keyboard = types.ReplyKeyboardRemove()
        await message.answer(text, reply_markup=remove_keyboard)
        await state.set_state(Registration.email)

    @dp.message(Registration.email)
    async def get_email(message: types.Message, state: FSMContext):
        await state.update_data(email=message.text)
        forgot_kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Забыли пароль?", callback_data="forget_password")]
        ])
        await message.answer(
            'Теперь необходимо ввести пароль.',
            reply_markup=forgot_kb
        )
        await state.set_state(Registration.password)

    @dp.message(Registration.password)
    async def get_password(message: types.Message, state: FSMContext):
        await state.update_data(password=message.text)
        data = await state.get_data()
        user = get_user_by_email(data['email'])
        if user:
            if verify_password(data['password'], user['password']) and user['verified'] == True:
                if change_db_users(user['email'], ('telegram', message.from_user.username)) != 'success':
                    error(f"DB save failed for user {user['email']}. Data: telegram")
                    await message.answer(
                        "🔧 Техническая ошибка. Администратор уже уведомлён",
                        reply_markup=types.ReplyKeyboardRemove()
                    )
                await message.answer(f'Ваша регистрация подтверждена. {user['username']}, давай начнём.')
                await state.clear()
            elif not verify_password(data['password'], user['password']):
                await message.answer('Пароль неверен, введите его заново.')
                await state.set_state(Registration.password)
            else:
                text = ('Вы еще не подтвердили регистрацию.\nСейчас вам на почту придет код подтверждения.\n'
                        'Отправьте его мне.')
                await message.answer(text)
                code = generate_verification_code()
                if change_db_users(user['email'], ('verification_code', code)) != 'success':
                    error(f"DB save failed for user {user['email']}. Data: {code}")
                    await message.answer(
                        "🔧 Техническая ошибка. Администратор уже уведомлён",
                        reply_markup=types.ReplyKeyboardRemove()
                    )
                #background_tasks.add_task(send_verification_email, user['email'], code)
                print(f'Verification code for {user['email']}: {code}')
                await state.set_state(Registration.verification)
        else:
            await message.answer('Назовите свое имя.')
            await state.set_state(Registration.name)

    @dp.message(Registration.verification)
    async def get_verification_code(message: types.Message, state: FSMContext):
        await state.update_data(verification_code=message.text)
        data = await state.get_data()
        user = get_user_by_email(data['email'])
        if data['verification_code'] == user['verification_code']:
            if change_db_users(data['email'], ('verified', 1)) != 'success':
                error(f"DB save failed for user {user['email']}. Data: verification")
                await message.answer(
                    "🔧 Техническая ошибка. Администратор уже уведомлён",
                    reply_markup=types.ReplyKeyboardRemove()
                )
            if not data['password']:
                await message.answer("Введите новый пароль.")
                await state.set_state(Registration.password)
            if change_db_users(data['email'], ('verified', 1)) != 'success':
                error(f"DB save failed for user {user['email']}. Data: verification")
                await message.answer(
                    "🔧 Техническая ошибка. Администратор уже уведомлён",
                    reply_markup=types.ReplyKeyboardRemove()
                )
            await message.answer("Вы вошли, можете начинать готовиться!")
            await state.clear()
        else:
            await message.answer("Код неверен. В случае неполадок обратитесь в поддержку. См. меню.")
            await state.set_state(Registration.verification)


    @dp.message(Registration.name)
    async def get_name(message: types.Message, state: FSMContext):
        await state.update_data(name=message.text)
        data = await state.get_data()
        code = generate_verification_code()
        if change_db_users(data['email'], ('verification_code', code)) != 'success':
            error(f"DB save failed for user {data['email']}. Data: {code}")
            await message.answer(
                "🔧 Техническая ошибка. Администратор уже уведомлён",
                reply_markup=types.ReplyKeyboardRemove()
            )
        #background_tasks.add_task(send_verification_email, data['email'], code)
        print(f'Verification code for {data['email']}: {code}')
        if save_user(data['email'], data['password'], data['name'], False, code):
            error(f"DB save failed for user {data['email']}.")
            await message.answer(
                "🔧 Техническая ошибка. Администратор уже уведомлён",
                reply_markup=types.ReplyKeyboardRemove()
            )
        await message.answer('Ваши данные сохранены. Код для подтверждения отправлен на почту. Введите его ниже.')
        await state.set_state(Registration.verification)

    @dp.callback_query(F.data == "forget_password")
    async def handle_forget_password(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        await state.update_data(password=None)
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer('Код для восстановления отправлен на почту. Введите его ниже.')
        await state.set_state(Registration.verification)