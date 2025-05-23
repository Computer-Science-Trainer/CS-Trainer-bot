from aiogram.fsm.state import State, StatesGroup

class Registration(StatesGroup):
    email = State()
    password = State()
    verification = State()
    name = State()

class LeaderBoard(StatesGroup):
    quantity = State()
    topic = State()

class Tests(StatesGroup):
    type_of_test = State()
    total_topic = State()
    recommended_test = State()
    topic = State()
    start_test = State()
    execute_test = State()
    end_test = State()
