from aiogram.fsm.state import State, StatesGroup

class Registration(StatesGroup):
    email = State()
    password = State()
    verification = State()
    name = State()
