"""Learner feedback on courses (Student 3: safe learner interaction).

Controls, in brief:
- Only a learner whose plan includes the course can read or post its feedback
  (the caller checks entitlement before using this module).
- Comments are stored as plain text. They may legitimately contain code such as
  ``<script>`` in the Secure Web course, so instead of stripping it the UI always
  renders comments with ``textContent``; the API never returns HTML.
- Control characters are removed, length is limited and each learner may post
  at most RATE_LIMIT_COUNT comments per RATE_LIMIT_WINDOW.
- A learner can edit or delete only their own comments. Another learner's id
  answers 404 so the API does not reveal which ids exist.
- Admins can hide or restore any comment. Hidden comments disappear for
  learners but remain for the moderation record.
- Audit events record ids and actions only, never the comment text.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from datetime import UTC, datetime, timedelta

MIN_LENGTH = 2
MAX_LENGTH = 500
RATE_LIMIT_COUNT = 5
RATE_LIMIT_WINDOW = timedelta(minutes=10)
LEARNER_PAGE_SIZE = 50
ADMIN_PAGE_SIZE = 50

_EXTRA_NEWLINES = re.compile(r"\n{3,}")


class FeedbackError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def clean_body(raw: object) -> str:
    """Validate a comment and return the text that will be stored."""
    if not isinstance(raw, str):
        raise FeedbackError("Feedback must be text.")
    if len(raw) > MAX_LENGTH * 4:
        raise FeedbackError(f"Feedback must be {MAX_LENGTH} characters or fewer.")
    text = unicodedata.normalize("NFC", raw.replace("\r\n", "\n").replace("\r", "\n"))
    # Drop control and format characters (null bytes, bidi overrides, zero-width
    # characters) but keep ordinary line breaks and tabs.
    text = "".join(
        char for char in text
        if char in "\n\t" or unicodedata.category(char) not in {"Cc", "Cf", "Cs", "Co", "Cn"}
    )
    text = _EXTRA_NEWLINES.sub("\n\n", text).strip()
    if len(text) < MIN_LENGTH:
        raise FeedbackError(f"Feedback must contain at least {MIN_LENGTH} characters.")
    if len(text) > MAX_LENGTH:
        raise FeedbackError(f"Feedback must be {MAX_LENGTH} characters or fewer.")
    return text


def display_name(full_name: str) -> str:
    """Show other learners a first name and initial only (minimal data)."""
    parts = full_name.split()
    if not parts:
        return "Learner"
    return parts[0] if len(parts) == 1 else f"{parts[0]} {parts[-1][0]}."


def _public(row: sqlite3.Row, user_id: int) -> dict:
    return {
        "id": row["id"],
        "author": display_name(row["full_name"]),
        "body": row["body"],
        "created_at": row["created_at"],
        "edited_at": row["edited_at"],
        "mine": row["user_id"] == user_id,
    }


def list_for_item(connection: sqlite3.Connection, user_id: int, item_id: int) -> list[dict]:
    rows = connection.execute(
        """
        SELECT f.id, f.user_id, f.body, f.created_at, f.edited_at, u.full_name
        FROM feedback f JOIN users u ON u.id = f.user_id
        WHERE f.learning_item_id = ? AND f.status = 'visible'
        ORDER BY f.id DESC LIMIT ?
        """,
        (item_id, LEARNER_PAGE_SIZE),
    ).fetchall()
    return [_public(row, user_id) for row in rows]


def create(connection: sqlite3.Connection, user_id: int, item_id: int, body: dict) -> dict:
    text = clean_body(body.get("body"))
    since = (_now() - RATE_LIMIT_WINDOW).isoformat()
    recent = connection.execute(
        "SELECT COUNT(*) FROM feedback WHERE user_id = ? AND created_at > ?",
        (user_id, since),
    ).fetchone()[0]
    if recent >= RATE_LIMIT_COUNT:
        raise FeedbackError(
            f"You can post up to {RATE_LIMIT_COUNT} comments every {int(RATE_LIMIT_WINDOW.total_seconds() // 60)} minutes. Please try again later.",
            429,
        )
    cursor = connection.execute(
        """
        INSERT INTO feedback (user_id, learning_item_id, body, status, created_at)
        VALUES (?, ?, ?, 'visible', ?)
        """,
        (user_id, item_id, text, _now().isoformat()),
    )
    return get_owned(connection, user_id, cursor.lastrowid)


def get_owned(connection: sqlite3.Connection, user_id: int, feedback_id: int) -> dict:
    row = connection.execute(
        """
        SELECT f.id, f.user_id, f.learning_item_id, f.body, f.created_at, f.edited_at, u.full_name
        FROM feedback f JOIN users u ON u.id = f.user_id
        WHERE f.id = ? AND f.user_id = ? AND f.status = 'visible'
        """,
        (feedback_id, user_id),
    ).fetchone()
    if not row:
        raise FeedbackError("Feedback was not found.", 404)
    return {**_public(row, user_id), "learning_item_id": row["learning_item_id"]}


def edit(connection: sqlite3.Connection, user_id: int, feedback_id: int, body: dict) -> dict:
    get_owned(connection, user_id, feedback_id)
    text = clean_body(body.get("body"))
    connection.execute(
        "UPDATE feedback SET body = ?, edited_at = ? WHERE id = ? AND user_id = ?",
        (text, _now().isoformat(), feedback_id, user_id),
    )
    return get_owned(connection, user_id, feedback_id)


def delete(connection: sqlite3.Connection, user_id: int, feedback_id: int) -> None:
    get_owned(connection, user_id, feedback_id)
    connection.execute("DELETE FROM feedback WHERE id = ? AND user_id = ?", (feedback_id, user_id))


def admin_list(connection: sqlite3.Connection) -> list[dict]:
    rows = connection.execute(
        """
        SELECT f.id, f.body, f.status, f.created_at, f.edited_at, f.moderated_at,
               u.full_name AS author, li.title AS item_title, m.full_name AS moderator
        FROM feedback f
        JOIN users u ON u.id = f.user_id
        JOIN learning_items li ON li.id = f.learning_item_id
        LEFT JOIN users m ON m.id = f.moderated_by
        ORDER BY f.id DESC LIMIT ?
        """,
        (ADMIN_PAGE_SIZE,),
    ).fetchall()
    return [dict(row) for row in rows]


def moderate(connection: sqlite3.Connection, admin_id: int, feedback_id: int, body: dict) -> str:
    action = str(body.get("action", "")).lower()
    if action not in {"hide", "restore"}:
        raise FeedbackError("Action must be hide or restore.")
    row = connection.execute("SELECT id FROM feedback WHERE id = ?", (feedback_id,)).fetchone()
    if not row:
        raise FeedbackError("Feedback was not found.", 404)
    status = "hidden" if action == "hide" else "visible"
    connection.execute(
        "UPDATE feedback SET status = ?, moderated_by = ?, moderated_at = ? WHERE id = ?",
        (status, admin_id, _now().isoformat(), feedback_id),
    )
    return status
