from aiogram import types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from httpx import HTTPStatusError
from .api_client import api_post
import logging
from aiogram.fsm.state import State, StatesGroup
from messages.locale import messages


MAX_USERNAME_LEN = 32
MAX_EMAIL_LEN = 320


class Registration(StatesGroup):
    email = State()
    name = State()
    password = State()
    password_repeat = State()
    verification = State()


class Auth(StatesGroup):
    email = State()
    password = State()


def register_registration(dp):
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message, state: FSMContext):
        username = message.from_user.username
        if not username:
            await message.answer(messages["registration"]["needUsername"])
            return
        try:
            resp = await api_post('auth/check-telegram', {'telegram_username': username})
            if resp.get('exists'):
                login = await api_post('auth/login-telegram', {'telegram_username': username})
                token = login.get('access_token') or login.get('token')
                if token:
                    await state.update_data(jwt_token=token)
                name = login.get('username', username)
                await message.answer(messages["registration"]["loginWelcome"].format(name=name))
            else:
                await state.update_data(telegram_username=username)
                await message.answer(messages["registration"]["enterEmail"])
                await state.set_state(Registration.email)
        except HTTPStatusError:
            await message.answer(messages["registration"]["connectionError"])

    @dp.message(Registration.email)
    async def link_email(message: types.Message, state: FSMContext):
        email = message.text
        data = await state.get_data()
        username = data.get('telegram_username')
        try:
            await api_post('auth/link-telegram', {'telegram_username': username, 'email': email})
            await message.answer(messages["registration"]["emailBound"])
            await state.clear()
        except HTTPStatusError as err:
            if err.response.status_code == 404:
                await state.update_data(email=email)
                await message.answer(messages["registration"]["emailNotFound"])
                await state.set_state(Registration.name)
                return
            if err.response.status_code == 422:
                await message.answer(messages["registration"]["unprocessableEntity"])
                return
            else:
                await message.answer(messages["registration"]["connectionError"])

    @dp.message(Registration.name)
    async def get_name(message: types.Message, state: FSMContext):
        await state.update_data(username=message.text)
        await message.answer(messages["registration"]["enterPassword"])
        await state.set_state(Registration.password)

    @dp.message(Registration.password)
    async def get_password(message: types.Message, state: FSMContext):
        await state.update_data(password=message.text)
        await message.answer(messages["registration"]["repeatPassword"])
        await state.set_state(Registration.password_repeat)

    @dp.message(Registration.password_repeat)
    async def get_password_repeat(message: types.Message, state: FSMContext):
        data = await state.get_data()
        pwd = data.get('password')
        if message.text != pwd:
            await message.answer(messages["registration"]["passwordMismatch"])
            await state.set_state(Registration.password)
            return
        username = data.get('telegram_username')
        email = data.get('email')
        name = data.get('username')
        try:
            await api_post('auth/register', {
                'telegram_username': username,
                'email': email,
                'password': pwd,
                'password_repeat': message.text,
                'username': name
            })
            await message.answer(messages["registration"]["verificationSent"])
            await state.set_state(Registration.verification)
        except HTTPStatusError as err:
            if err.response.status_code == 400:
                await message.answer(messages["registration"]["passwordError"])
                return
            else:
                await message.answer(messages["registration"]["connectionError"])

    @dp.message(Registration.verification)
    async def verify_code(message: types.Message, state: FSMContext):
        data = await state.get_data()
        email = data.get('email')
        try:
            await api_post('auth/verify', {'email': email, 'code': message.text})
            await message.answer(messages["registration"]["registrationCompleted"])
            await state.clear()
        except HTTPStatusError:
            await message.answer('Неверный код. Попробуйте снова.')
            await state.set_state(Registration.verification)

    @dp.callback_query(F.data == "forget_password")
    async def handle_forget_password(
            callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        await state.update_data(password=None)
        await callback.message.edit_reply_markup(reply_markup=None)
        data = await state.get_data()
        email = data.get('email')
        try:
            await api_post('auth/recover', {'email': email})
            await callback.message.answer(messages["registration"]["forgotPasswordSent"])
            await state.set_state(Registration.verification)
        except HTTPStatusError as exc:
            logging.error("Password recovery failed for %s: %s", email, exc)
            await callback.message.answer(messages["registration"]["forgotPasswordError"])

    @dp.message(Command("login"))
    async def cmd_login(message: types.Message, state: FSMContext):
        await message.answer(messages["registration"]["enterEmailLogin"])
        await state.set_state(Auth.email)

    @dp.message(Auth.email)
    async def process_login_email(message: types.Message, state: FSMContext):
        await state.update_data(email=message.text)
        await message.answer(messages["registration"]["enterPasswordLogin"])
        await state.set_state(Auth.password)

    @dp.message(Auth.password)
    async def process_login_password(
            message: types.Message, state: FSMContext):
        data = await state.get_data()
        email = data.get('email')
        password = message.text
        try:
            resp = await api_post('auth/login', {'email': email, 'password': password})
            token = resp.get('access_token') or resp.get('token')
            if token:
                await state.update_data(jwt_token=token)
                await message.answer(messages["registration"]["loginSuccess"])
            else:
                await message.answer(messages["registration"]["tokenError"])
            await state.clear()
        except HTTPStatusError:
            await message.answer(messages["registration"]["loginError"])
