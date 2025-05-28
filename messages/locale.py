import os
import json

BASE_PATH = os.path.dirname(__file__)
ru_path = os.path.join(BASE_PATH, 'ru.json')
with open(ru_path, encoding='utf-8') as f:
    messages = json.load(f)
