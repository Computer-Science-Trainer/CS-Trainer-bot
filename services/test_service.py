import datetime
import random
from typing import List, Dict
from sqlalchemy.orm import Session
from database import execute
import json
from sqlalchemy import func, Integer
from services.achievement_service import award_achievement, get_user_achievements
import logging
logger = logging.getLogger(__name__)

def get_test(test_id, user_id):
    row = execute(
            "SELECT topics, questions, created_at FROM tests WHERE id = %s AND user_id = %s",
            (test_id, user_id), fetchone=True
        )
    row = execute(
        "SELECT id FROM tests WHERE user_id = %s ORDER BY created_at DESC LIMIT 1",
        (user_id,), fetchone=True
    )
    test_id = row[0]
    return test_id

def update_questions(test_id_to, test_id_from):
    info = execute(
            "SELECT questions FROM tests WHERE id = %s",
            (test_id_from), fetchone=True
        )
    execute(
        "UPDATE tests SET questions = %s WHERE id = %s",
        (info, test_id_to),
    )

def get_questions(test_id, user_id):
    row = execute(
        "SELECT topics, questions, created_at FROM tests WHERE id = %s AND user_id = %s",
        (test_id, user_id), fetchone=True
    )
    questions_json = row[1]
    if questions_json:
        question_ids = json.loads(questions_json)
        if question_ids:
            questions = []
            placeholders = ",".join(["%s"] * len(question_ids))
            rows = execute(
                f"SELECT id, title, question_text, question_type, difficulty, options, correct_answer "
                f"FROM current_questions WHERE id IN ({placeholders})",
                tuple(question_ids)
            )
            id_to_row = {r[0]: r for r in rows}
            for qid in question_ids:
                r = id_to_row.get(qid)
                if r:
                    questions.append({
                        "id": r[0],
                        "title": r[1],
                        "question_text": r[2],
                        "question_type": r[3],
                        "difficulty": r[4],
                        "options": json.loads(r[5]) if r[5] else [],
                        "answer": r[5],
                        "user_answer": ""
                    })
            return questions

def ending(test_id, user_id, passed, total, average, earned_score):
    questions = get_questions(test_id, user_id)
    difficulty_map = {"easy": 1, "medium": 2, "hard": 5}
    total_minutes = sum(
        difficulty_map.get(q["difficulty"], 1)
        for q in questions
    )
    moscow_tz = datetime.timezone(datetime.timedelta(hours=3))
    end_time = datetime.datetime.now(
        moscow_tz) + datetime.timedelta(minutes=total_minutes)
    execute(
        """
        UPDATE tests
        SET passed = %s,
            total = %s,
            average = %s,
            earned_score = %s
        WHERE id = %s
        """,
        (end_time, total, average, earned_score, test_id)
    )