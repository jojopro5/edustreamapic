"""Server-owned module assessments, saved attempts and grading.

Question keys remain in the database snapshot and are revealed only after submit.
The caller checks role, course visibility and subscription for every operation.
"""
from __future__ import annotations

import json
import secrets
from copy import deepcopy
from datetime import UTC, datetime

from assessment_content import COURSE_ASSESSMENTS

PASS_PERCENT = 80
MODULE_QUESTIONS = 8
FINAL_PER_MODULE = 4
RANDOM = secrets.SystemRandom()


class AssessmentError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def definitions(item_id: int) -> list[dict]:
    course = COURSE_ASSESSMENTS.get(item_id)
    if not course:
        raise AssessmentError("Assessments were not found for this course.", 404)
    modules = [
        {"id": module["id"], "title": module["title"], "description": module["description"],
         "kind": "module", "question_count": MODULE_QUESTIONS,
         "estimated_minutes": module.get("estimated_minutes", 15)}
        for module in course["modules"]
    ]
    return modules + [{
        "id": "final", "title": "Final course assessment", "kind": "final",
        "description": "Apply what you learned across all three modules. Pass each module quiz to unlock this assessment.",
        "question_count": len(modules) * FINAL_PER_MODULE, "estimated_minutes": 25,
    }]


def best_scores(connection, user_id: int, item_id: int) -> dict[str, int]:
    return {row["assessment_id"]: row["best"] for row in connection.execute(
        "SELECT assessment_id, MAX(score) AS best FROM assessment_attempts "
        "WHERE user_id = ? AND learning_item_id = ? AND status = 'submitted' GROUP BY assessment_id",
        (user_id, item_id),
    )}


def completion(connection, user_id: int, item_id: int) -> dict:
    scores = best_scores(connection, user_id, item_id)
    ids = [definition["id"] for definition in definitions(item_id)]
    passed = sum(scores.get(key, -1) >= PASS_PERCENT for key in ids)
    return {"completed": passed == len(ids), "passed_count": passed, "total_assessments": len(ids)}


def modules_passed(connection, user_id: int, item_id: int) -> bool:
    scores = best_scores(connection, user_id, item_id)
    return all(scores.get(module["id"], -1) >= PASS_PERCENT for module in COURSE_ASSESSMENTS[item_id]["modules"])


def overview(connection, user_id: int, item_id: int) -> dict:
    assessments = definitions(item_id)
    scores = best_scores(connection, user_id, item_id)
    final_unlocked = modules_passed(connection, user_id, item_id)
    for assessment in assessments:
        key = assessment["id"]
        history = [dict(row) for row in connection.execute(
            "SELECT id AS attempt_id, score, submitted_at, json_array_length(questions_json) AS question_count "
            "FROM assessment_attempts WHERE user_id = ? AND learning_item_id = ? "
            "AND assessment_id = ? AND status = 'submitted' ORDER BY id DESC LIMIT 20",
            (user_id, item_id, key),
        )]
        for row in history:
            row["passed"] = row["score"] >= PASS_PERCENT
        count = connection.execute(
            "SELECT COUNT(*) FROM assessment_attempts WHERE user_id = ? AND learning_item_id = ? "
            "AND assessment_id = ? AND status = 'submitted'", (user_id, item_id, key),
        ).fetchone()[0]
        draft = connection.execute(
            "SELECT id FROM assessment_attempts WHERE user_id = ? AND learning_item_id = ? "
            "AND assessment_id = ? AND status = 'in_progress'", (user_id, item_id, key),
        ).fetchone()
        locked = key == "final" and not final_unlocked
        assessment.update({
            "locked": locked,
            "lock_reason": "Pass all three module quizzes with at least 80% to unlock the final assessment." if locked else "",
            "best_score": scores.get(key), "passed": scores.get(key, -1) >= PASS_PERCENT,
            "attempt_count": count, "draft_attempt_id": draft["id"] if draft else None, "history": history,
        })
    return {"course": {"item_id": item_id, "title": COURSE_ASSESSMENTS[item_id]["title"],
                       "pass_percent": PASS_PERCENT, **completion(connection, user_id, item_id)},
            "assessments": assessments}


def owned_attempt(connection, user_id: int, attempt_id: int):
    row = connection.execute(
        "SELECT * FROM assessment_attempts WHERE id = ? AND user_id = ?", (attempt_id, user_id),
    ).fetchone()
    if not row:
        raise AssessmentError("Assessment attempt was not found.", 404)
    return row


def public_attempt(connection, row) -> dict:
    questions = json.loads(row["questions_json"])
    result = json.loads(row["result_json"]) if row["status"] == "submitted" else None
    if result:
        result["best_score"] = best_scores(connection, row["user_id"], row["learning_item_id"])[row["assessment_id"]]
        result["course_completed"] = completion(connection, row["user_id"], row["learning_item_id"])["completed"]
    return {
        "id": row["id"], "item_id": row["learning_item_id"], "assessment_id": row["assessment_id"],
        "title": row["title"], "kind": row["kind"], "status": row["status"],
        "questions": [{"id": question["id"], "prompt": question["prompt"],
                       "options": [{"id": option["id"], "text": option["text"]} for option in question["options"]]}
                      for question in questions],
        "answers": json.loads(row["answers_json"]), "pass_percent": PASS_PERCENT,
        "question_count": len(questions), "started_at": row["started_at"], "saved_at": row["saved_at"],
        "submitted_at": row["submitted_at"], "result": result,
    }


def start(connection, user_id: int, item_id: int, body: dict) -> dict:
    key = body.get("assessment_id") if isinstance(body, dict) else None
    definition = next((entry for entry in definitions(item_id) if entry["id"] == key), None)
    if not definition:
        raise AssessmentError("Select a valid module quiz or final assessment.", 404)
    if key == "final" and not modules_passed(connection, user_id, item_id):
        raise AssessmentError("Pass all three module quizzes before starting the final assessment.", 403)
    existing = connection.execute(
        "SELECT * FROM assessment_attempts WHERE user_id = ? AND learning_item_id = ? "
        "AND assessment_id = ? AND status = 'in_progress'", (user_id, item_id, key),
    ).fetchone()
    if existing:
        return public_attempt(connection, existing)
    previous = connection.execute(
        "SELECT questions_json FROM assessment_attempts WHERE user_id = ? AND learning_item_id = ? "
        "AND assessment_id = ? AND status = 'submitted' ORDER BY id DESC LIMIT 1", (user_id, item_id, key),
    ).fetchone()
    excluded = {question["id"] for question in json.loads(previous["questions_json"])} if previous else set()
    chosen = []
    for module in COURSE_ASSESSMENTS[item_id]["modules"]:
        if key != "final" and module["id"] != key:
            continue
        count = FINAL_PER_MODULE if key == "final" else MODULE_QUESTIONS
        eligible = [question for question in module["questions"] if question["id"] not in excluded]
        if len(eligible) < count:
            raise AssessmentError("A new question set is not available yet. Please contact your educator.", 503)
        chosen.extend(deepcopy(RANDOM.sample(eligible, count)))
    RANDOM.shuffle(chosen)
    for question in chosen:
        RANDOM.shuffle(question["options"])
    timestamp = now()
    cursor = connection.execute(
        "INSERT INTO assessment_attempts (user_id, learning_item_id, assessment_id, title, kind, status, "
        "questions_json, answers_json, started_at, saved_at) VALUES (?, ?, ?, ?, ?, 'in_progress', ?, '{}', ?, ?)",
        (user_id, item_id, key, definition["title"], definition["kind"], json.dumps(chosen), timestamp, timestamp),
    )
    return public_attempt(connection, owned_attempt(connection, user_id, cursor.lastrowid))


def validated_answers(row, body, require_complete: bool) -> dict:
    answers = body.get("answers") if isinstance(body, dict) else None
    questions = {question["id"]: question for question in json.loads(row["questions_json"])}
    if not isinstance(answers, dict) or not set(answers).issubset(questions):
        raise AssessmentError("Answers must belong to the questions in this attempt.")
    if require_complete and set(answers) != set(questions):
        raise AssessmentError("Answer every question before submitting the assessment.")
    for key, selected in answers.items():
        allowed = {option["id"] for option in questions[key]["options"]}
        if not isinstance(selected, str) or selected not in allowed:
            raise AssessmentError("Choose one of the displayed options for each question.")
    return answers


def save(connection, row, body) -> dict:
    if row["status"] != "in_progress":
        raise AssessmentError("Submitted attempts are read-only. Start a new attempt to try again.", 409)
    answers = validated_answers(row, body, require_complete=False)
    connection.execute("UPDATE assessment_attempts SET answers_json = ?, saved_at = ? WHERE id = ?",
                       (json.dumps(answers), now(), row["id"]))
    return public_attempt(connection, owned_attempt(connection, row["user_id"], row["id"]))


def submit(connection, row, body) -> dict:
    # Repeated requests after a successful submit never create another grade.
    if row["status"] == "submitted":
        return public_attempt(connection, row)
    if row["assessment_id"] == "final" and not modules_passed(connection, row["user_id"], row["learning_item_id"]):
        raise AssessmentError("Pass all module quizzes before submitting the final assessment.", 403)
    answers = validated_answers(row, body, require_complete=True)
    questions = json.loads(row["questions_json"])
    feedback = [{"question_id": question["id"],
                 "correct": answers[question["id"]] == question["correct_option_id"],
                 "selected_option_id": answers[question["id"]], "correct_option_id": question["correct_option_id"],
                 "explanation": question["explanation"]} for question in questions]
    correct = sum(item["correct"] for item in feedback)
    score = round(correct * 100 / len(questions))
    result = {"score": score, "correct": correct, "total_questions": len(questions),
              "passed": score >= PASS_PERCENT, "feedback": feedback}
    timestamp = now()
    connection.execute(
        "UPDATE assessment_attempts SET status = 'submitted', answers_json = ?, result_json = ?, "
        "score = ?, saved_at = ?, submitted_at = ? WHERE id = ?",
        (json.dumps(answers), json.dumps(result), score, timestamp, timestamp, row["id"]),
    )
    connection.execute(
        "INSERT INTO audit_events (user_id, event_type, details, created_at) VALUES (?, 'assessment_submitted', ?, ?)",
        (row["user_id"], f"Course {row['learning_item_id']} / {row['assessment_id']}: {score}% (attempt {row['id']})", timestamp),
    )
    return public_attempt(connection, owned_attempt(connection, row["user_id"], row["id"]))
