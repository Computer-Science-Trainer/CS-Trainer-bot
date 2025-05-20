from aiogram import types
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from services.user_service import save_user, change_db_users, get_user_by_email
from stations import Registration

def register_handlers(dp):
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message, state: FSMContext):
        await state.set_state(Registration.name)

    @dp.message(Registration.name)
    async def get_name(message: types.Message, state: FSMContext):
        await state.update_data(name=message.text)
        await message.answer("Введите вашу почту:")
        await state.set_state(Registration.email)

    @dp.message(Registration.email)
    async def get_email(message: types.Message, state: FSMContext):
        await state.update_data(email=message.text)
        await message.answer("Введите пароль:")
        await state.set_state(Registration.password)

    @dp.message(Registration.password)
    async def get_password(message: types.Message, state: FSMContext):
        data = await state.get_data()
        data["password"] = message.text
        await message.answer(f"Регистрация завершена!\nИмя: {data['name']}\nEmail: {data['email']}")
        print(state.get_data())
        await state.clear() 