"""Learner registration and account profiles (Student 1: identity and profiles).

Controls, in brief:
- Self-registration creates learner accounts only. Educator and admin accounts
  are created by an administrator, so nobody can sign up into a privileged role.
- Passwords: 10 to 128 characters, not a common password, not built from the
  email address, stored with salted PBKDF2 (server.make_password).
- Names and bios are trimmed, length-limited and stripped of control
  characters; the UI always renders them as text.
- A profile can only be read or changed by its own account. Changing the
  password requires the current password and ends the account's other sessions.
- Registration is rate-limited per client address.
"""

from __future__ import annotations

import re
import threading
import time
import unicodedata

NAME_MIN, NAME_MAX = 2, 80
BIO_MAX = 400
PASSWORD_MIN, PASSWORD_MAX = 10, 128
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,24}")
# A short blocklist for the prototype; a production system would check a breached-password list.
COMMON_PASSWORDS = frozenset({
    "password", "password1", "password123", "passw0rd", "qwerty", "qwerty123", "letmein", "welcome",
    "welcome1", "iloveyou", "admin", "admin123", "123456", "1234567890", "12345678", "abc123",
    "monkey", "dragon", "football", "baseball", "sunshine", "princess", "edustream", "edustream1",
    "edustream123", "learn123!", "teach123!", "admin123!", "changeme", "trustno1",
})
REGISTRATIONS_PER_CLIENT = 5
REGISTRATION_WINDOW_SECONDS = 60 * 60


class AccountError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _clean_text(value: object, field: str, minimum: int, maximum: int, multiline: bool = False) -> str:
    if not isinstance(value, str):
        raise AccountError(f"{field} must be text.")
    text = unicodedata.normalize("NFC", value.replace("\r\n", "\n"))
    allowed = "\n" if multiline else ""
    text = "".join(char for char in text if char in allowed or unicodedata.category(char) not in {"Cc", "Cf", "Cs", "Co", "Cn"})
    text = re.sub(r"[ \t]+", " ", text).strip()
    if not multiline:
        text = text.replace("\n", " ")
    if len(text) < minimum:
        raise AccountError(f"{field} must contain at least {minimum} characters.")
    if len(text) > maximum:
        raise AccountError(f"{field} must be {maximum} characters or fewer.")
    return text


def clean_name(value: object) -> str:
    return _clean_text(value, "Name", NAME_MIN, NAME_MAX)


def clean_bio(value: object) -> str:
    if value in (None, ""):
        return ""
    return _clean_text(value, "Bio", 0, BIO_MAX, multiline=True)


def clean_email(value: object) -> str:
    if not isinstance(value, str):
        raise AccountError("Enter a valid email address.")
    email = value.strip().lower()
    if len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
        raise AccountError("Enter a valid email address.")
    return email


def check_password(password: object, email: str) -> str:
    if not isinstance(password, str):
        raise AccountError("Password must be text.")
    if len(password) < PASSWORD_MIN:
        raise AccountError(f"Use a password of at least {PASSWORD_MIN} characters. A short phrase works well.")
    if len(password) > PASSWORD_MAX:
        raise AccountError(f"Passwords can be at most {PASSWORD_MAX} characters.")
    lowered = password.lower()
    if lowered in COMMON_PASSWORDS or len(set(password)) < 4:
        raise AccountError("That password is too common or too easy to guess. Choose another.")
    local_part = email.split("@", 1)[0].lower()
    if lowered == email or (len(local_part) >= 4 and local_part in lowered):
        raise AccountError("Your password must not contain your email address.")
    return password


class RegistrationThrottle:
    """Limit new accounts per client address inside a rolling window."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: dict[str, list[float]] = {}

    def allow(self, client: str) -> bool:
        now = time.monotonic()
        with self._lock:
            recent = [t for t in self._events.get(client, []) if now - t < REGISTRATION_WINDOW_SECONDS]
            self._events[client] = recent
            return len(recent) < REGISTRATIONS_PER_CLIENT

    def record(self, client: str) -> None:
        with self._lock:
            self._events.setdefault(client, []).append(time.monotonic())

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


def public_profile(row) -> dict:
    return {
        "id": row["id"],
        "full_name": row["full_name"],
        "email": row["email"],
        "role": row["role"],
        "bio": row["bio"] or "",
        "created_at": row["created_at"],
    }
