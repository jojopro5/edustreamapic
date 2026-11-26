from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import mimetypes
import os
import re
import secrets
import sqlite3
import threading
import time
import traceback
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

import uploads

from quizzes import QUIZZES, public_quiz
import backups
import assessments
import feedback


ROOT = Path(__file__).resolve().parent
STATIC_ROOT = ROOT / "static"
DATA_ROOT = ROOT / "data"
DB_PATH = DATA_ROOT / "edustream.db"
SCHEMA_PATH = ROOT / "database" / "schema.sql"

SESSION_COOKIE = "edustream_session"
SESSION_TTL = timedelta(hours=8)
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

# Login throttling: failed attempts inside the window are counted per
# (client address, email) and per client address. Successful sign-ins are free.
LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_MAX_FAILURES_PER_ACCOUNT = 5
LOGIN_MAX_FAILURES_PER_CLIENT = 20


class _DiscardBody:
    """Stands in for wfile after the headers of a HEAD response."""

    def __init__(self, wfile):
        self._wfile = wfile

    def write(self, data) -> int:
        return len(data)

    def flush(self) -> None:
        self._wfile.flush()

    def __getattr__(self, name):
        # closed, close() and the rest still reach the real socket file.
        return getattr(self._wfile, name)


class ClosingConnection(sqlite3.Connection):
    """Commit or roll back a context block, then release the database file."""

    def __exit__(self, exc_type, exc_value, traceback):
        result = super().__exit__(exc_type, exc_value, traceback)
        self.close()
        return result


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso_now() -> str:
    return utc_now().replace(microsecond=0).isoformat()


def connect_db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH, timeout=10, factory=ClosingConnection)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def make_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 180_000)
    return salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, digest_hex: str) -> bool:
    _, candidate = make_password(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(candidate, digest_hex)


def seed_database(connection: sqlite3.Connection) -> None:
    if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
        return

    users = [
        ("Amina Clarke", "learner@edustream.local", "Learn123!", "learner"),
        ("Noah Bennett", "educator@edustream.local", "Teach123!", "educator"),
        ("System Administrator", "admin@edustream.local", "Admin123!", "admin"),
    ]
    for name, email, password, role in users:
        salt, digest = make_password(password)
        connection.execute(
            "INSERT INTO users (full_name, email, password_salt, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (name, email, salt, digest, role, iso_now()),
        )

    connection.executemany(
        "INSERT INTO plans (name, code, price_monthly, description) VALUES (?, ?, ?, ?)",
        [
            ("Starter", "starter", 12.00, "Core courses for learners beginning their study plan."),
            ("Plus", "plus", 24.00, "The complete catalogue with advanced practice and progress insights."),
            ("Team", "team", 39.00, "Full access for collaborative learning and team reporting."),
        ],
    )

    educator_id = connection.execute(
        "SELECT id FROM users WHERE role = 'educator'"
    ).fetchone()[0]
    items = [
        (
            "Digital Safety Foundations",
            "Cybersecurity",
            "A practical introduction to passwords, phishing awareness and safe online behaviour.",
            "course",
            55,
            educator_id,
            "approved",
        ),
        (
            "SQL Essentials",
            "Data",
            "Learn how relational tables, keys and queries work through guided examples.",
            "course",
            75,
            educator_id,
            "approved",
        ),
        (
            "Secure Web Application Design",
            "Development",
            "Apply authentication, authorisation and input-validation patterns to a web project.",
            "course",
            95,
            educator_id,
            "approved",
        ),
        (
            "Privacy by Design Workshop",
            "Cybersecurity",
            "A scenario-based workshop for identifying privacy risks before implementation.",
            "workshop",
            45,
            educator_id,
            "pending",
        ),
    ]
    connection.executemany(
        """
        INSERT INTO learning_items
            (title, category, description, content_type, duration_minutes, created_by, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [(*item, iso_now()) for item in items],
    )

    plan_ids = {
        row["code"]: row["id"]
        for row in connection.execute("SELECT id, code FROM plans")
    }
    item_ids = [row["id"] for row in connection.execute("SELECT id FROM learning_items ORDER BY id")]
    entitlements = [
        (plan_ids["starter"], item_ids[0]),
        (plan_ids["starter"], item_ids[1]),
        (plan_ids["plus"], item_ids[0]),
        (plan_ids["plus"], item_ids[1]),
        (plan_ids["plus"], item_ids[2]),
        (plan_ids["team"], item_ids[0]),
        (plan_ids["team"], item_ids[1]),
        (plan_ids["team"], item_ids[2]),
    ]
    connection.executemany(
        "INSERT INTO plan_entitlements (plan_id, learning_item_id) VALUES (?, ?)",
        entitlements,
    )

    learner_id = connection.execute(
        "SELECT id FROM users WHERE role = 'learner'"
    ).fetchone()[0]
    start_date = utc_now().date()
    end_date = start_date + timedelta(days=30)
    cursor = connection.execute(
        """
        INSERT INTO subscriptions (user_id, plan_id, status, start_date, end_date, created_at)
        VALUES (?, ?, 'active', ?, ?, ?)
        """,
        (learner_id, plan_ids["starter"], start_date.isoformat(), end_date.isoformat(), iso_now()),
    )
    subscription_id = cursor.lastrowid
    connection.execute(
        "INSERT INTO payments (user_id, subscription_id, amount, status, paid_at) VALUES (?, ?, ?, 'paid', ?)",
        (learner_id, subscription_id, 12.00, iso_now()),
    )
    connection.execute(
        "INSERT INTO progress (user_id, learning_item_id, progress_percent, updated_at) VALUES (?, ?, ?, ?)",
        (learner_id, item_ids[0], 65, iso_now()),
    )
    connection.commit()


def initialize_database(reset: bool = False) -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    if reset and DB_PATH.exists():
        DB_PATH.unlink()
    with connect_db() as connection:
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(learning_items)")}
        if "language" not in columns:
            # Existing curated courses are English; keep all records and progress.
            connection.execute(
                "ALTER TABLE learning_items ADD COLUMN language TEXT NOT NULL DEFAULT 'en' CHECK (language IN ('en', 'id'))"
            )
        # Review feedback for educators; older databases gain the columns in place.
        for column in ("review_note", "reviewed_at"):
            if column not in columns:
                connection.execute(f"ALTER TABLE learning_items ADD COLUMN {column} TEXT")
        seed_database(connection)


def record_audit(connection: sqlite3.Connection, user_id: int | None, event_type: str, details: str) -> None:
    connection.execute(
        "INSERT INTO audit_events (user_id, event_type, details, created_at) VALUES (?, ?, ?, ?)",
        (user_id, event_type, details[:500], iso_now()),
    )


DEMO_ACCOUNTS = [
    {"role": "learner", "email": "learner@edustream.local", "password": "Learn123!"},
    {"role": "educator", "email": "educator@edustream.local", "password": "Teach123!"},
    {"role": "admin", "email": "admin@edustream.local", "password": "Admin123!"},
]
CONTENT_TYPES = frozenset({"course", "video", "article", "quiz", "workshop"})


def validated_content(body: dict) -> dict:
    """Check the educator-editable fields of a learning item and return them cleaned."""
    title = str(body.get("title", "")).strip()
    category = str(body.get("category", "")).strip()
    description = str(body.get("description", "")).strip()
    content_type = str(body.get("content_type", "course")).strip().lower()
    language = str(body.get("language", "en")).strip().lower()
    try:
        duration = int(body.get("duration_minutes", 0))
    except (TypeError, ValueError):
        duration = 0
    if not 4 <= len(title) <= 100:
        raise ValueError("Title must contain between 4 and 100 characters.")
    if not 3 <= len(category) <= 40:
        raise ValueError("Category must contain between 3 and 40 characters.")
    if not 20 <= len(description) <= 500:
        raise ValueError("Description must contain between 20 and 500 characters.")
    if content_type not in CONTENT_TYPES:
        raise ValueError("Select a supported content type.")
    if language not in {"en", "id"}:
        raise ValueError("Select English or Bahasa Indonesia as the content language.")
    if not 5 <= duration <= 600:
        raise ValueError("Duration must be between 5 and 600 minutes.")
    return {"title": title, "category": category, "description": description,
            "content_type": content_type, "language": language, "duration_minutes": duration}


SUBSCRIPTION_PERIOD_DAYS = 30
# Plans kept in the database (for existing records) but no longer offered or sold.
HIDDEN_PLAN_CODES = frozenset({"team"})


def offered_plans(connection: sqlite3.Connection) -> list[dict]:
    return [
        dict(row)
        for row in connection.execute("SELECT * FROM plans ORDER BY price_monthly")
        if row["code"] not in HIDDEN_PLAN_CODES
    ]


def active_subscription(connection: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT subscriptions.*, plans.name AS plan_name, plans.code AS plan_code,
               plans.price_monthly, plans.description AS plan_description
        FROM subscriptions
        JOIN plans ON plans.id = subscriptions.plan_id
        WHERE subscriptions.user_id = ?
          AND subscriptions.status = 'active'
          AND date(subscriptions.end_date) >= date('now')
        ORDER BY subscriptions.id DESC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()


def has_course_assessments(item_id: int) -> bool:
    """True when the item has a practice quiz and module assessment banks."""
    quiz = QUIZZES.get(item_id)
    return bool(quiz and quiz.get("questions")) and assessments.has_assessments(item_id)


def learner_visible(item: dict | sqlite3.Row) -> bool:
    """Show learners approved, non-Indonesian items that have a quiz.

    Visibility comes from the item's review status and language plus whether a
    quiz and assessment bank exist for it, not from a fixed list of IDs. Whether
    a learner can open an item is still decided by their plan in has_entitlement().
    """
    return (
        item["status"] == "approved"
        and item["language"] != "id"
        and has_course_assessments(item["id"])
    )


def course_completion(connection: sqlite3.Connection, user_id: int, item_id: int, progress_percent: int) -> dict:
    """Single completion rule used by the dashboard counter and the progress endpoint.

    A course with assessments is complete only when every assessment is passed.
    The self-reported progress slider cannot complete an assessed course on its own.
    A course without assessments is complete at 100% progress.
    """
    status = assessments.completion(connection, user_id, item_id)
    if status["total_assessments"]:
        completed = status["completed"]
    else:
        completed = progress_percent >= 100
    return {**status, "completed": completed}


def has_entitlement(connection: sqlite3.Connection, user_id: int, item_id: int) -> bool:
    item = connection.execute(
        "SELECT id, status, language FROM learning_items WHERE id = ?", (item_id,)
    ).fetchone()
    if not item or not learner_visible(item):
        return False
    return connection.execute(
        """
        SELECT 1
        FROM subscriptions
        JOIN plan_entitlements ON plan_entitlements.plan_id = subscriptions.plan_id
        JOIN learning_items ON learning_items.id = plan_entitlements.learning_item_id
        WHERE subscriptions.user_id = ?
          AND plan_entitlements.learning_item_id = ?
          AND subscriptions.status = 'active'
          AND date(subscriptions.end_date) >= date('now')
          AND learning_items.status = 'approved'
        LIMIT 1
        """,
        (user_id, item_id),
    ).fetchone() is not None


def grant_default_entitlements(connection: sqlite3.Connection, item_id: int) -> None:
    """Include a newly approved item in the full-catalogue plans (Plus and Team)."""
    for row in connection.execute("SELECT id FROM plans WHERE code IN ('plus', 'team')").fetchall():
        connection.execute(
            "INSERT OR IGNORE INTO plan_entitlements (plan_id, learning_item_id) VALUES (?, ?)",
            (row["id"], item_id),
        )


def row_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


def hash_token(token: str) -> str:
    # Only a digest is stored, so a copy of the database cannot be replayed as live sessions.
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(connection: sqlite3.Connection, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    now = utc_now()
    connection.execute(
        "INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (hash_token(token), user_id, now.isoformat(timespec="microseconds"), (now + SESSION_TTL).isoformat(timespec="microseconds")),
    )
    return token


def session_user_id(token: str | None) -> int | None:
    if not token:
        return None
    with connect_db() as connection:
        connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (utc_now().isoformat(timespec="microseconds"),))
        row = connection.execute(
            "SELECT user_id FROM sessions WHERE token_hash = ?",
            (hash_token(token),),
        ).fetchone()
    return row["user_id"] if row else None


def delete_session(token: str | None) -> None:
    if not token:
        return
    with connect_db() as connection:
        connection.execute("DELETE FROM sessions WHERE token_hash = ?", (hash_token(token),))


def is_loopback_host(host: str) -> bool:
    return host in LOOPBACK_HOSTS or host.startswith("127.")


class LoginThrottle:
    """Sliding-window counter of failed sign-ins, kept in memory."""

    def __init__(self) -> None:
        self._failures: dict[tuple, list[float]] = {}
        self._lock = threading.Lock()

    def _recent(self, key: tuple, now: float) -> list[float]:
        stamps = [stamp for stamp in self._failures.get(key, []) if now - stamp < LOGIN_WINDOW_SECONDS]
        if stamps:
            self._failures[key] = stamps
        else:
            self._failures.pop(key, None)
        return stamps

    def retry_after(self, client: str, email: str) -> int:
        """Seconds until another attempt is allowed, or 0 if allowed now."""
        now = time.monotonic()
        wait = 0.0
        with self._lock:
            for key, limit in (((client, email), LOGIN_MAX_FAILURES_PER_ACCOUNT), ((client,), LOGIN_MAX_FAILURES_PER_CLIENT)):
                stamps = self._recent(key, now)
                if len(stamps) >= limit:
                    wait = max(wait, LOGIN_WINDOW_SECONDS - (now - stamps[-limit]))
        return int(wait) + 1 if wait > 0 else 0

    def record_failure(self, client: str, email: str) -> None:
        now = time.monotonic()
        with self._lock:
            for key in ((client, email), (client,)):
                self._recent(key, now)
                self._failures.setdefault(key, []).append(now)

    def record_success(self, client: str, email: str) -> None:
        with self._lock:
            self._failures.pop((client, email), None)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()


LOGIN_THROTTLE = LoginThrottle()


class EduStreamHandler(BaseHTTPRequestHandler):
    server_version = "EduStream/1.0"

    def log_message(self, fmt: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {self.address_string()} {fmt % args}")

    def _security_headers(self, api: bool = False) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'",
        )
        if api:
            self.send_header("Cache-Control", "no-store")

    def _session_cookie(self, value: str, max_age: int) -> str:
        cookie = f"{SESSION_COOKIE}={value}; Path=/; HttpOnly; SameSite=Lax; Max-Age={max_age}"
        if getattr(self.server, "secure_cookies", False):
            cookie += "; Secure"
        return cookie

    def _json(self, payload: dict | list, status: int = 200, cookies: list[str] | None = None,
              headers: dict[str, str] | None = None) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._security_headers(api=True)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        for cookie in cookies or []:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(data)

    def _error(self, message: str, status: int = 400) -> None:
        self._json({"ok": False, "error": message}, status)

    def _body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("Invalid request length")
        if length <= 0 or length > 1_000_000:
            raise ValueError("Request body is missing or too large")
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("Request body must be valid JSON")
        if not isinstance(data, dict):
            raise ValueError("Request body must be a JSON object")
        return data

    def _session_token(self) -> str | None:
        cookie_header = self.headers.get("Cookie")
        if not cookie_header:
            return None
        cookie = SimpleCookie()
        cookie.load(cookie_header)
        morsel = cookie.get(SESSION_COOKIE)
        return morsel.value if morsel else None

    def _current_user(self) -> dict | None:
        user_id = session_user_id(self._session_token())
        if user_id is None:
            return None
        with connect_db() as connection:
            user = connection.execute(
                "SELECT id, full_name, email, role FROM users WHERE id = ? AND is_active = 1",
                (user_id,),
            ).fetchone()
        return row_dict(user)

    def _require_user(self, roles: set[str] | None = None) -> dict | None:
        user = self._current_user()
        if not user:
            self._error("Please sign in to continue.", HTTPStatus.UNAUTHORIZED)
            return None
        if roles and user["role"] not in roles:
            self._error("Your account does not have permission for this action.", HTTPStatus.FORBIDDEN)
            return None
        return user

    def _serve_static(self, request_path: str) -> None:
        relative = "index.html" if request_path in {"", "/"} else unquote(request_path.lstrip("/"))
        target = (STATIC_ROOT / relative).resolve()
        try:
            target.relative_to(STATIC_ROOT.resolve())
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not target.is_file():
            if Path(relative).suffix:
                # A missing asset is a real 404; only extensionless paths fall back to the app.
                self._error("File not found.", HTTPStatus.NOT_FOUND)
                return
            target = STATIC_ROOT / "index.html"
        data = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self._security_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def end_headers(self) -> None:
        super().end_headers()
        if self.command == "HEAD":
            # A HEAD response carries the GET headers but never a body.
            self.wfile = _DiscardBody(self.wfile)

    def do_HEAD(self) -> None:
        self._run_safely(self._handle_get)

    def _cross_site_error(self, path: str) -> str | None:
        """Reject state-changing requests that a browser sent from another site.

        SameSite=Lax already keeps the session cookie off most cross-site POSTs; this is a
        second layer for older browsers and sibling subdomains.
        """
        fetch_site = self.headers.get("Sec-Fetch-Site")
        if fetch_site and fetch_site not in {"same-origin", "none"}:
            return "Cross-site requests are not allowed."
        origin = self.headers.get("Origin")
        if origin is not None and (origin == "null" or urlparse(origin).netloc != self.headers.get("Host", "")):
            return "Cross-site requests are not allowed."
        if re.fullmatch(r"/api/content/\d+/attachment", path):
            # File uploads are raw bytes; the custom header forces a CORS preflight.
            if not self.headers.get("X-File-Name"):
                return "File uploads must include the X-File-Name header."
            return None
        content_type = self.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if content_type != "application/json":
            return "Requests must be sent as application/json."
        return None

    def _run_safely(self, handler) -> None:
        """Answer with a JSON 500 instead of dropping the connection on an unexpected error."""
        try:
            handler()
        except Exception:
            traceback.print_exc()
            try:
                self._error("Something went wrong on the server. Please try again.", HTTPStatus.INTERNAL_SERVER_ERROR)
            except Exception:
                pass

    def do_GET(self) -> None:
        self._run_safely(self._handle_get)

    def do_POST(self) -> None:
        self._run_safely(self._handle_post)

    def _handle_get(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if not path.startswith("/api/"):
            self._serve_static(parsed.path)
            return

        if path == "/api/admin/backups":
            user = self._require_user({"admin"})
            if user:
                self._json({"ok": True, "backups": backups.list_backups(DB_PATH)})
            return

        if path == "/api/session":
            user = self._current_user()
            with connect_db() as connection:
                plans = offered_plans(connection)
            demo = DEMO_ACCOUNTS if getattr(self.server, "demo_logins", True) else []
            self._json({"ok": True, "authenticated": bool(user), "user": user, "plans": plans, "demo_accounts": demo})
            return

        if path == "/api/dashboard":
            user = self._require_user()
            if not user:
                return
            self._json({"ok": True, **self._dashboard(user)})
            return

        match = re.fullmatch(r"/api/feedback/(\d+)", path)
        if match:
            user = self._require_user({"learner"})
            if user:
                self._feedback_request(user, "list", item_id=int(match.group(1)))
            return

        match = re.fullmatch(r"/api/assessments/(\d+)", path)
        if match:
            user = self._require_user({"learner"})
            if user:
                self._assessment_request(user, item_id=int(match.group(1)))
            return

        match = re.fullmatch(r"/api/assessment-attempts/(\d+)", path)
        if match:
            user = self._require_user({"learner"})
            if user:
                self._assessment_request(user, action="read", attempt_id=int(match.group(1)))
            return

        match = re.fullmatch(r"/api/quiz/(\d+)", path)
        if match:
            user = self._require_user({"learner"})
            if user:
                self._get_quiz(user, int(match.group(1)))
            return

        match = re.fullmatch(r"/api/content/(\d+)/attachment", path)
        if match:
            user = self._require_user()
            if user:
                self._download_attachment(user, int(match.group(1)))
            return

        match = re.fullmatch(r"/api/access/(\d+)", path)
        if match:
            user = self._require_user({"learner"})
            if not user:
                return
            item_id = int(match.group(1))
            with connect_db() as connection:
                item = connection.execute(
                    "SELECT id, title, category, description, content_type, language, duration_minutes, status FROM learning_items WHERE id = ?",
                    (item_id,),
                ).fetchone()
                if not item or not has_entitlement(connection, user["id"], item_id):
                    if item:
                        # Unknown ids are not logged, so probing ids cannot flood the audit log.
                        record_audit(connection, user["id"], "access_denied", f"Learning item {item_id}")
                        connection.commit()
                    self._error("This learning item is unavailable or not included in your active subscription.", HTTPStatus.FORBIDDEN)
                    return
                record_audit(connection, user["id"], "content_accessed", f"Learning item {item_id}")
                connection.commit()
                attachment = uploads.public_info(uploads.file_record(connection, item_id))
            self._json(
                {
                    "ok": True,
                    "item": {**dict(item), "attachment": attachment},
                    "lesson": {
                        "heading": "Lesson available",
                        "body": "Your plan includes this course. Work through the materials below, then record your study progress.",
                    },
                }
            )
            return

        self._error("API endpoint not found.", HTTPStatus.NOT_FOUND)

    def _handle_post(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        cross_site = self._cross_site_error(path)
        if cross_site:
            self._error(cross_site, HTTPStatus.FORBIDDEN)
            return
        try:
            if path == "/api/login":
                self._login(self._body())
                return
            if path == "/api/logout":
                delete_session(self._session_token())
                self._json({"ok": True}, cookies=[self._session_cookie("", 0)])
                return
            if path == "/api/progress":
                user = self._require_user({"learner"})
                if user:
                    self._update_progress(user, self._body())
                return
            if path == "/api/subscription":
                user = self._require_user({"learner"})
                if user:
                    self._change_subscription(user, self._body())
                return
            match = re.fullmatch(r"/api/content/(\d+)/attachment", path)
            if match:
                user = self._require_user({"educator", "admin"})
                if user:
                    self._upload_attachment(user, int(match.group(1)))
                return
            if path == "/api/content":
                user = self._require_user({"educator", "admin"})
                if user:
                    self._create_content(user, self._body())
                return
            match = re.fullmatch(r"/api/feedback/(\d+)", path)
            if match:
                user = self._require_user({"learner"})
                if user:
                    self._feedback_request(user, "create", item_id=int(match.group(1)), body=self._body())
                return
            match = re.fullmatch(r"/api/feedback-entries/(\d+)/(edit|delete)", path)
            if match:
                user = self._require_user({"learner"})
                if user:
                    self._feedback_request(user, match.group(2), feedback_id=int(match.group(1)), body=self._body())
                return
            match = re.fullmatch(r"/api/admin/feedback/(\d+)/moderate", path)
            if match:
                user = self._require_user({"admin"})
                if user:
                    self._feedback_request(user, "moderate", feedback_id=int(match.group(1)), body=self._body())
                return
            match = re.fullmatch(r"/api/assessments/(\d+)/start", path)
            if match:
                user = self._require_user({"learner"})
                if user:
                    self._assessment_request(user, action="start", item_id=int(match.group(1)), body=self._body())
                return
            match = re.fullmatch(r"/api/assessment-attempts/(\d+)/(save|submit)", path)
            if match:
                user = self._require_user({"learner"})
                if user:
                    self._assessment_request(user, action=match.group(2), attempt_id=int(match.group(1)), body=self._body())
                return
            match = re.fullmatch(r"/api/quiz/(\d+)/submit", path)
            if match:
                user = self._require_user({"learner"})
                if user:
                    self._submit_quiz(user, int(match.group(1)), self._body())
                return
            match = re.fullmatch(r"/api/content/(\d+)/resubmit", path)
            if match:
                user = self._require_user({"educator"})
                if user:
                    self._resubmit_content(user, int(match.group(1)), self._body())
                return
            match = re.fullmatch(r"/api/admin/content/(\d+)/review", path)
            if match:
                user = self._require_user({"admin"})
                if user:
                    self._review_content(user, int(match.group(1)), self._body())
                return
            if path == "/api/admin/backups":
                user = self._require_user({"admin"})
                if user:
                    self._create_backup(user)
                return
            match = re.fullmatch(r"/api/admin/backups/([A-Za-z0-9.-]{1,80})/(verify|restore)", path)
            if match:
                user = self._require_user({"admin"})
                if user:
                    if match.group(2) == "verify":
                        self._verify_backup(user, match.group(1))
                    else:
                        self._restore_backup(user, match.group(1), self._body())
                return
            self._error("API endpoint not found.", HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self._error(str(exc), HTTPStatus.BAD_REQUEST)

    def _login(self, body: dict) -> None:
        email = str(body.get("email", "")).strip().lower()
        password = str(body.get("password", ""))
        if not email or not password:
            raise ValueError("Email and password are required.")
        client = self.client_address[0]
        wait = LOGIN_THROTTLE.retry_after(client, email)
        if wait:
            self._json(
                {"ok": False, "error": "Too many failed sign-in attempts. Please wait and try again."},
                HTTPStatus.TOO_MANY_REQUESTS,
                headers={"Retry-After": str(wait)},
            )
            return
        with connect_db() as connection:
            user = connection.execute(
                "SELECT * FROM users WHERE email = ? AND is_active = 1",
                (email,),
            ).fetchone()
            if not user or not verify_password(password, user["password_salt"], user["password_hash"]):
                LOGIN_THROTTLE.record_failure(client, email)
                self._error("The email or password is incorrect.", HTTPStatus.UNAUTHORIZED)
                return
            LOGIN_THROTTLE.record_success(client, email)
            token = create_session(connection, user["id"])
            record_audit(connection, user["id"], "login", "Successful sign in")
            connection.commit()
        self._json(
            {"ok": True, "user": {"id": user["id"], "full_name": user["full_name"], "email": user["email"], "role": user["role"]}},
            cookies=[self._session_cookie(token, int(SESSION_TTL.total_seconds()))],
        )

    def _dashboard(self, user: dict) -> dict:
        with connect_db() as connection:
            plans = offered_plans(connection)
            if user["role"] == "learner":
                subscription = active_subscription(connection, user["id"])
                plan_id = subscription["plan_id"] if subscription else -1
                items = [
                    dict(row)
                    for row in connection.execute(
                        """
                        SELECT li.id, li.title, li.category, li.description, li.content_type, li.language, li.status,
                               li.duration_minutes,
                               CASE WHEN pe.learning_item_id IS NULL THEN 0 ELSE 1 END AS entitled,
                               COALESCE(p.progress_percent, 0) AS progress_percent
                        FROM learning_items li
                        LEFT JOIN plan_entitlements pe
                          ON pe.learning_item_id = li.id AND pe.plan_id = ?
                        LEFT JOIN progress p
                          ON p.learning_item_id = li.id AND p.user_id = ?
                        WHERE li.status = 'approved'
                        ORDER BY li.id
                        """,
                        (plan_id, user["id"]),
                    )
                    if learner_visible(row)
                ]
                for item in items:
                    item["has_quiz"] = True
                    item["quiz_question_count"] = sum(entry["question_count"] for entry in assessments.definitions(item["id"]))
                    assessment_status = course_completion(connection, user["id"], item["id"], item["progress_percent"])
                    item["completed"] = assessment_status["completed"]
                    item["assessment_completed"] = assessment_status["completed"]
                    item["assessments_passed"] = assessment_status["passed_count"]
                    item["assessment_count"] = assessment_status["total_assessments"]
                payments = [
                    dict(row)
                    for row in connection.execute(
                        "SELECT amount, status, paid_at FROM payments WHERE user_id = ? ORDER BY id DESC LIMIT 5",
                        (user["id"],),
                    )
                ]
                entitled = [item for item in items if item["entitled"]]
                average_progress = round(sum(item["progress_percent"] for item in entitled) / len(entitled)) if entitled else 0
                return {
                    "role": "learner",
                    "user": user,
                    "subscription": row_dict(subscription),
                    "plans": plans,
                    "items": items,
                    "payments": payments,
                    "stats": {
                        "available": len(entitled),
                        "completed": sum(1 for item in entitled if item["completed"]),
                        "average_progress": average_progress,
                        "locked": sum(1 for item in items if not item["entitled"]),
                    },
                }

            if user["role"] == "educator":
                items = [
                    dict(row)
                    for row in connection.execute(
                        """
                        SELECT id, title, category, description, content_type, language, duration_minutes, status, created_at, review_note
                        FROM learning_items WHERE created_by = ? ORDER BY id DESC
                        """,
                        (user["id"],),
                    )
                ]
                for item in items:
                    item["attachment"] = uploads.public_info(uploads.file_record(connection, item["id"]))
                return {
                    "role": "educator",
                    "user": user,
                    "items": items,
                    "stats": {
                        "total": len(items),
                        "approved": sum(1 for item in items if item["status"] == "approved"),
                        "pending": sum(1 for item in items if item["status"] == "pending"),
                        "rejected": sum(1 for item in items if item["status"] == "rejected"),
                    },
                }

            pending_items = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT li.id, li.title, li.category, li.description, li.content_type, li.language,
                           li.duration_minutes, li.status, li.created_at, u.full_name AS educator_name
                    FROM learning_items li
                    JOIN users u ON u.id = li.created_by
                    WHERE li.status = 'pending'
                    ORDER BY li.created_at
                    """
                )
            ]
            for item in pending_items:
                item["attachment"] = uploads.public_info(uploads.file_record(connection, item["id"]))
            audit = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT ae.id, ae.event_type, ae.details, ae.created_at,
                           COALESCE(u.full_name, 'System') AS user_name
                    FROM audit_events ae
                    LEFT JOIN users u ON u.id = ae.user_id
                    ORDER BY ae.id DESC LIMIT 30
                    """
                )
            ]
            counts = {
                row["role"]: row["count"]
                for row in connection.execute("SELECT role, COUNT(*) AS count FROM users GROUP BY role")
            }
            approved_count = connection.execute(
                "SELECT COUNT(*) FROM learning_items WHERE status = 'approved'"
            ).fetchone()[0]
            active_count = connection.execute(
                "SELECT COUNT(*) FROM subscriptions WHERE status = 'active' AND date(end_date) >= date('now')"
            ).fetchone()[0]
            return {
                "role": "admin",
                "user": user,
                "pending_items": pending_items,
                "audit": audit,
                "feedback": feedback.admin_list(connection),
                "plans": plans,
                "stats": {
                    "learners": counts.get("learner", 0),
                    "educators": counts.get("educator", 0),
                    "active_subscriptions": active_count,
                    "approved_content": approved_count,
                    "pending_content": len(pending_items),
                },
            }

    def _assessment_request(self, user: dict, action: str = "overview", item_id: int | None = None,
                            attempt_id: int | None = None, body: dict | None = None) -> None:
        try:
            with connect_db() as connection:
                if action in {"start", "save", "submit"}:
                    # Serialize competing saves/submits and avoid duplicate draft attempts.
                    connection.execute("BEGIN IMMEDIATE")
                row = None
                if attempt_id is not None:
                    row = assessments.owned_attempt(connection, user["id"], attempt_id)
                    item_id = row["learning_item_id"]
                if not has_entitlement(connection, user["id"], item_id):
                    raise assessments.AssessmentError("An active subscription that includes this course is required.", 403)
                if action == "overview":
                    payload = assessments.overview(connection, user["id"], item_id)
                elif action == "start":
                    payload = {"attempt": assessments.start(connection, user["id"], item_id, body)}
                elif action == "save":
                    payload = {"attempt": assessments.save(connection, row, body)}
                elif action == "submit":
                    payload = {"attempt": assessments.submit(connection, row, body)}
                else:
                    payload = {"attempt": assessments.public_attempt(connection, row)}
            self._json({"ok": True, **payload})
        except assessments.AssessmentError as error:
            self._error(str(error), error.status)

    def _feedback_request(self, user: dict, action: str, item_id: int | None = None,
                          feedback_id: int | None = None, body: dict | None = None) -> None:
        body = body or {}
        try:
            with connect_db() as connection:
                if action == "moderate":
                    status = feedback.moderate(connection, user["id"], feedback_id, body)
                    record_audit(connection, user["id"], "feedback_moderated", f"Feedback {feedback_id}: {status}")
                    connection.commit()
                    self._json({"ok": True, "message": "Feedback hidden." if status == "hidden" else "Feedback restored.", "status": status})
                    return
                if feedback_id is not None:
                    item_id = feedback.get_owned(connection, user["id"], feedback_id)["learning_item_id"]
                if not has_entitlement(connection, user["id"], item_id):
                    record_audit(connection, user["id"], "feedback_access_denied", f"Learning item {item_id}")
                    connection.commit()
                    raise feedback.FeedbackError("An active subscription that includes this course is required.", 403)
                if action == "list":
                    payload = {"feedback": feedback.list_for_item(connection, user["id"], item_id)}
                elif action == "create":
                    try:
                        entry = feedback.create(connection, user["id"], item_id, body)
                    except feedback.FeedbackError as error:
                        if error.status == 429:
                            record_audit(connection, user["id"], "feedback_rate_limited", f"Learning item {item_id}")
                            connection.commit()
                        raise
                    record_audit(connection, user["id"], "feedback_posted", f"Feedback {entry['id']} on learning item {item_id}")
                    payload = {"feedback": entry, "message": "Thanks, your feedback is posted."}
                elif action == "edit":
                    entry = feedback.edit(connection, user["id"], feedback_id, body)
                    record_audit(connection, user["id"], "feedback_edited", f"Feedback {feedback_id}")
                    payload = {"feedback": entry, "message": "Feedback updated."}
                else:
                    feedback.delete(connection, user["id"], feedback_id)
                    record_audit(connection, user["id"], "feedback_deleted", f"Feedback {feedback_id}")
                    payload = {"message": "Feedback deleted."}
                connection.commit()
            self._json({"ok": True, **payload})
        except feedback.FeedbackError as error:
            self._error(str(error), error.status)

    def _quiz_for_user(self, connection: sqlite3.Connection, user: dict, item_id: int) -> dict | None:
        quiz = QUIZZES.get(item_id)
        if not quiz or not quiz.get("questions"):
            self._error("There is no practice quiz for this learning item.", HTTPStatus.NOT_FOUND)
            return None
        if not has_entitlement(connection, user["id"], item_id):
            record_audit(connection, user["id"], "quiz_access_denied", f"Learning item {item_id}")
            connection.commit()
            self._error("An active subscription that includes this course is required for its quiz.", HTTPStatus.FORBIDDEN)
            return None
        return quiz

    def _get_quiz(self, user: dict, item_id: int) -> None:
        with connect_db() as connection:
            quiz = self._quiz_for_user(connection, user, item_id)
            if not quiz:
                return
            last_attempt = connection.execute(
                """
                SELECT id AS attempt_id, score, correct_count AS correct, total_questions, created_at
                FROM quiz_attempts WHERE user_id = ? AND learning_item_id = ?
                ORDER BY id DESC LIMIT 1
                """,
                (user["id"], item_id),
            ).fetchone()
        self._json({"ok": True, "quiz": public_quiz(quiz), "last_attempt": row_dict(last_attempt)})

    def _submit_quiz(self, user: dict, item_id: int, body: dict) -> None:
        with connect_db() as connection:
            quiz = self._quiz_for_user(connection, user, item_id)
            if not quiz:
                return
            answers = body.get("answers") if isinstance(body, dict) else None
            question_ids = {question["id"] for question in quiz["questions"]}
            if not isinstance(answers, dict) or set(answers) != question_ids:
                raise ValueError("Please answer every question before submitting the quiz.")
            feedback = []
            for question in quiz["questions"]:
                selected = answers[question["id"]]
                allowed = {option["id"] for option in question["options"]}
                if not isinstance(selected, str) or selected not in allowed:
                    raise ValueError("Each answer must be one of the options shown in the quiz.")
                feedback.append(
                    {
                        "question_id": question["id"],
                        "correct": selected == question["correct_option_id"],
                        "selected_option_id": selected,
                        "correct_option_id": question["correct_option_id"],
                        "explanation": question["explanation"],
                    }
                )
            correct = sum(item["correct"] for item in feedback)
            total = len(feedback)
            score = round(correct * 100 / total)
            created_at = iso_now()
            cursor = connection.execute(
                """
                INSERT INTO quiz_attempts
                    (user_id, learning_item_id, score, correct_count, total_questions, answers_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user["id"], item_id, score, correct, total, json.dumps(answers), created_at),
            )
            attempt_id = cursor.lastrowid
            record_audit(connection, user["id"], "quiz_submitted", f"Learning item {item_id}: {correct}/{total} ({score}%)")
            connection.commit()
        self._json(
            {
                "ok": True,
                "result": {
                    "attempt_id": attempt_id,
                    "score": score,
                    "correct": correct,
                    "total_questions": total,
                    "passed": score >= quiz["pass_percent"],
                    "feedback": feedback,
                    "created_at": created_at,
                },
            }
        )

    def _upload_root(self) -> Path:
        return DB_PATH.parent / "uploads"

    def _upload_attachment(self, user: dict, item_id: int) -> None:
        """Receive a raw file body; the display name comes from the X-File-Name header."""
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        raw_name = unquote(self.headers.get("X-File-Name", ""))
        with connect_db() as connection:
            item = connection.execute(
                "SELECT id, title, status, created_by FROM learning_items WHERE id = ?", (item_id,)
            ).fetchone()
            if not item:
                self._error("Learning item was not found.", HTTPStatus.NOT_FOUND)
                return
            try:
                if length < 0:
                    raise uploads.UploadError("Invalid request length.", reason="bad_length")
                if length > uploads.MAX_BYTES:
                    # Refuse before reading so an oversized body is never held in memory.
                    self.close_connection = True
                    raise uploads.UploadError("Files must be 5 MB or smaller.", 413, "too_large")
                data = self.rfile.read(length) if length else b""
                info = uploads.store(connection, self._upload_root(), item, user, raw_name, data)
            except uploads.UploadError as error:
                record_audit(connection, user["id"], "content_file_rejected", f"Learning item {item_id}: {error.reason}")
                connection.commit()
                self._error(str(error), error.status)
                return
            record_audit(
                connection, user["id"], "content_file_uploaded",
                f"Learning item {item_id}: {info['type']}, {info['size_bytes']} bytes, sha256 {info['sha256'][:16]}"
                + (" (replaced)" if info["replaced"] else ""),
            )
            connection.commit()
        self._json({"ok": True, "message": "File attached.", "attachment": info})

    def _download_attachment(self, user: dict, item_id: int) -> None:
        with connect_db() as connection:
            item = connection.execute(
                "SELECT id, status, language, created_by FROM learning_items WHERE id = ?", (item_id,)
            ).fetchone()
            if user["role"] == "learner":
                allowed = bool(item) and has_entitlement(connection, user["id"], item_id)
            elif user["role"] == "educator":
                allowed = bool(item) and item["created_by"] == user["id"]
            else:
                allowed = bool(item)
            record = uploads.file_record(connection, item_id) if allowed else None
            if not allowed:
                record_audit(connection, user["id"], "content_file_denied", f"Learning item {item_id}")
                connection.commit()
                self._error("This file is unavailable or not included in your active subscription.", HTTPStatus.FORBIDDEN)
                return
            if not record:
                self._error("This learning item has no attached file.", HTTPStatus.NOT_FOUND)
                return
            path = self._upload_root() / record["stored_name"]
            if not path.is_file():
                self._error("The attached file is missing from storage.", HTTPStatus.NOT_FOUND)
                return
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != record["sha256"]:
                record_audit(connection, user["id"], "content_file_integrity_failed", f"Learning item {item_id}")
                connection.commit()
                self._error("The attached file failed its integrity check.", HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            record_audit(connection, user["id"], "content_file_downloaded", f"Learning item {item_id}")
            connection.commit()
        self.send_response(HTTPStatus.OK)
        self.send_header("Referrer-Policy", "no-referrer")
        for name, value in uploads.download_headers(record).items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _update_progress(self, user: dict, body: dict) -> None:
        try:
            item_id = int(body.get("item_id"))
            progress = int(body.get("progress"))
        except (TypeError, ValueError):
            raise ValueError("Learning item and progress are required.")
        if not 0 <= progress <= 100:
            raise ValueError("Progress must be between 0 and 100.")
        with connect_db() as connection:
            if not has_entitlement(connection, user["id"], item_id):
                self._error("You cannot update progress for a locked learning item.", HTTPStatus.FORBIDDEN)
                return
            completed_at = iso_now() if progress == 100 else None
            connection.execute(
                """
                INSERT INTO progress (user_id, learning_item_id, progress_percent, completed_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, learning_item_id)
                DO UPDATE SET progress_percent = excluded.progress_percent,
                              completed_at = excluded.completed_at,
                              updated_at = excluded.updated_at
                """,
                (user["id"], item_id, progress, completed_at, iso_now()),
            )
            record_audit(connection, user["id"], "progress_updated", f"Learning item {item_id}: {progress}%")
            connection.commit()
            status = course_completion(connection, user["id"], item_id, progress)
        if status["completed"]:
            message = "Course completed. Well done!"
        elif progress == 100 and status["total_assessments"]:
            remaining = status["total_assessments"] - status["passed_count"]
            message = (
                f"Progress saved at 100%. Pass the remaining {remaining} "
                f"assessment{'s' if remaining != 1 else ''} to complete this course."
            )
        else:
            message = f"Your progress is saved at {progress}%."
        self._json({
            "ok": True,
            "message": message,
            "progress": progress,
            "completed": status["completed"],
            "assessments_passed": status["passed_count"],
            "assessment_count": status["total_assessments"],
        })

    def _change_subscription(self, user: dict, body: dict) -> None:
        """Quote a plan change or renewal, and charge only when the learner confirms it.

        Without "confirm": true the endpoint returns a quote and records nothing.
        Paid days are kept: the new 30-day period starts from the current end date
        when the active subscription has not yet expired, otherwise from today.
        """
        try:
            plan_id = int(body.get("plan_id"))
        except (TypeError, ValueError):
            raise ValueError("Select a valid subscription plan.")
        confirmed = body.get("confirm") is True
        with connect_db() as connection:
            plan = connection.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
            if not plan:
                raise ValueError("The selected subscription plan does not exist.")
            if plan["code"] in HIDDEN_PLAN_CODES:
                raise ValueError("The selected subscription plan is no longer offered.")
            current = active_subscription(connection, user["id"])
            today = utc_now().date()
            current_end = datetime.fromisoformat(current["end_date"]).date() if current else None
            period_start = max(today, current_end) if current_end else today
            new_end = period_start + timedelta(days=SUBSCRIPTION_PERIOD_DAYS)
            action = "renew" if current and current["plan_id"] == plan_id else ("change" if current else "subscribe")
            quote = {
                "action": action,
                "plan_id": plan["id"],
                "plan_name": plan["name"],
                "amount": plan["price_monthly"],
                "current_plan_name": current["plan_name"] if current else None,
                "current_end_date": current_end.isoformat() if current_end else None,
                "new_end_date": new_end.isoformat(),
                "days_kept": (current_end - today).days if current_end and current_end > today else 0,
            }
            if not confirmed:
                self._json({"ok": True, "requires_confirmation": True, "quote": quote})
                return
            connection.execute(
                "UPDATE subscriptions SET status = 'cancelled' WHERE user_id = ? AND status = 'active'",
                (user["id"],),
            )
            cursor = connection.execute(
                """
                INSERT INTO subscriptions (user_id, plan_id, status, start_date, end_date, created_at)
                VALUES (?, ?, 'active', ?, ?, ?)
                """,
                (user["id"], plan_id, today.isoformat(), new_end.isoformat(), iso_now()),
            )
            connection.execute(
                "INSERT INTO payments (user_id, subscription_id, amount, status, paid_at) VALUES (?, ?, ?, 'paid', ?)",
                (user["id"], cursor.lastrowid, plan["price_monthly"], iso_now()),
            )
            verb = "renewed" if action == "renew" else "changed to"
            record_audit(
                connection, user["id"], "subscription_changed",
                f"Plan {verb} {plan['name']}; access ends {new_end.isoformat()}",
            )
            connection.commit()
        message = (
            f"Your {plan['name']} plan is renewed until {new_end.isoformat()}."
            if action == "renew"
            else f"Your {plan['name']} plan is now active until {new_end.isoformat()}."
        )
        self._json({"ok": True, "message": message, "quote": quote})

    def _create_content(self, user: dict, body: dict) -> None:
        fields = validated_content(body)
        status = "approved" if user["role"] == "admin" else "pending"
        with connect_db() as connection:
            cursor = connection.execute(
                """
                INSERT INTO learning_items
                    (title, category, description, content_type, language, duration_minutes, created_by, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (fields["title"], fields["category"], fields["description"], fields["content_type"],
                 fields["language"], fields["duration_minutes"], user["id"], status, iso_now()),
            )
            if status == "approved":
                # Admin-published items skip review, so grant plan access here too.
                grant_default_entitlements(connection, cursor.lastrowid)
            record_audit(connection, user["id"], "content_created", f"Learning item {cursor.lastrowid}: {fields['title']} ({status})")
            connection.commit()
        self._json({"ok": True, "message": "Content submitted for approval." if status == "pending" else "Content published.", "item_id": cursor.lastrowid})

    def _resubmit_content(self, user: dict, item_id: int, body: dict) -> None:
        """Let an educator edit a rejected item and send it back for review."""
        fields = validated_content(body)
        with connect_db() as connection:
            item = connection.execute(
                "SELECT id, status, created_by FROM learning_items WHERE id = ?", (item_id,)
            ).fetchone()
            if not item or item["created_by"] != user["id"]:
                self._error("Learning item was not found.", HTTPStatus.NOT_FOUND)
                return
            if item["status"] != "rejected":
                self._error("Only rejected items can be edited and resubmitted.", HTTPStatus.CONFLICT)
                return
            connection.execute(
                """
                UPDATE learning_items
                SET title = ?, category = ?, description = ?, content_type = ?, language = ?,
                    duration_minutes = ?, status = 'pending'
                WHERE id = ?
                """,
                (fields["title"], fields["category"], fields["description"], fields["content_type"],
                 fields["language"], fields["duration_minutes"], item_id),
            )
            record_audit(connection, user["id"], "content_resubmitted", f"Learning item {item_id}: {fields['title']}")
            connection.commit()
        self._json({"ok": True, "message": "Changes sent for review.", "item_id": item_id})

    def _review_content(self, user: dict, item_id: int, body: dict) -> None:
        decision = str(body.get("decision", "")).lower()
        if decision not in {"approved", "rejected"}:
            raise ValueError("Decision must be approved or rejected.")
        reason = str(body.get("reason", "")).strip()
        if decision == "rejected" and not 10 <= len(reason) <= 500:
            raise ValueError("Give the educator a reason for the rejection (10 to 500 characters).")
        with connect_db() as connection:
            item = connection.execute("SELECT id, title, status FROM learning_items WHERE id = ?", (item_id,)).fetchone()
            if not item:
                self._error("Learning item was not found.", HTTPStatus.NOT_FOUND)
                return
            if item["status"] != "pending":
                # Published or already rejected items are not re-reviewed from here, so a
                # stale or scripted request cannot pull a live course away from learners.
                self._error(f"This item was already {item['status']}. Only pending items can be reviewed.", HTTPStatus.CONFLICT)
                return
            connection.execute(
                "UPDATE learning_items SET status = ?, review_note = ?, reviewed_at = ? WHERE id = ?",
                (decision, reason if decision == "rejected" else None, iso_now(), item_id),
            )
            if decision == "approved":
                grant_default_entitlements(connection, item_id)
            details = f"{item['title']}: {decision}" + (f" ({reason})" if decision == "rejected" else "")
            record_audit(connection, user["id"], "content_reviewed", details)
            connection.commit()
        self._json({"ok": True, "message": f"Content {decision}."})

    def _create_backup(self, user: dict) -> None:
        ref = secrets.token_hex(4)
        try:
            manifest = backups.create_backup(DB_PATH, f"{user['full_name']} (user {user['id']})")
        except (OSError, sqlite3.Error, backups.BackupError) as exc:
            with connect_db() as connection:
                record_audit(connection, user["id"], "backup_failed", f"outcome=failure ref={ref} reason={exc}")
                connection.commit()
            self._error("The backup could not be created. Please try again.", HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        with connect_db() as connection:
            record_audit(connection, user["id"], "backup_created",
                         f"outcome=success ref={ref} backup={manifest['file']} sha256={manifest['sha256'][:16]}")
            connection.commit()
        self._json({"ok": True, "message": "Backup created and verified.", "backup": manifest["file"]})

    def _verify_backup(self, user: dict, name: str) -> None:
        ref = secrets.token_hex(4)
        if not backups.exists(DB_PATH, name):
            self._error("Backup was not found.", HTTPStatus.NOT_FOUND)
            return
        result = backups.verify_backup(DB_PATH, name)
        with connect_db() as connection:
            if result["ok"]:
                record_audit(connection, user["id"], "backup_verified", f"outcome=success ref={ref} backup={name}")
            else:
                record_audit(connection, user["id"], "backup_verify_failed",
                             f"outcome=failure ref={ref} backup={name} checks={' | '.join(result['problems'])}")
            connection.commit()
        self._json({"ok": True, "name": name, "valid": result["ok"], "problems": result["problems"]})

    def _restore_backup(self, user: dict, name: str, body: dict) -> None:
        ref = secrets.token_hex(4)
        if body.get("confirm") != name:
            raise ValueError("Type the backup name to confirm the restore.")
        if not backups.exists(DB_PATH, name):
            self._error("Backup was not found.", HTTPStatus.NOT_FOUND)
            return
        try:
            outcome = backups.restore_backup(DB_PATH, name, f"{user['full_name']} (user {user['id']})")
        except backups.BackupError as exc:
            with connect_db() as connection:
                record_audit(connection, user["id"], "backup_restore_refused",
                             f"outcome=refused ref={ref} backup={name} checks={' | '.join(exc.problems)}")
                connection.commit()
            self._json({"ok": False, "error": str(exc), "problems": exc.problems}, HTTPStatus.CONFLICT)
            return
        # Bring an older backup up to the current schema, then end every session:
        # accounts and roles may differ in the restored data (C-T4-BR-09).
        initialize_database()
        sessions = globals().get("SESSIONS")
        if isinstance(sessions, dict):
            sessions.clear()
        with connect_db() as connection:
            if connection.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'sessions'").fetchone():
                connection.execute("DELETE FROM sessions")
            actor = user["id"] if connection.execute("SELECT 1 FROM users WHERE id = ?", (user["id"],)).fetchone() else None
            record_audit(connection, actor, "backup_restored",
                         f"outcome=success ref={ref} backup={name} by={user['email']} "
                         f"safety_backup={outcome['safety_backup']['file']} carried_audit_events={outcome['carried_audit']}")
            connection.commit()
        self._json(
            {"ok": True, "message": "Backup restored. Everyone, including you, must sign in again.",
             "safety_backup": outcome["safety_backup"]["file"]},
            cookies=[f"{SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"],
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the EduStream prototype server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    parser.add_argument("--reset", action="store_true", help="Reset the prototype database")
    parser.add_argument(
        "--secure-cookies",
        choices=("auto", "on", "off"),
        default=os.environ.get("EDUSTREAM_SECURE_COOKIES", "auto"),
        help="Mark the session cookie Secure (HTTPS only). 'auto' turns it on unless --host is a loopback address.",
    )
    parser.add_argument(
        "--demo-logins",
        choices=("on", "off"),
        default=os.environ.get("EDUSTREAM_DEMO_LOGINS", "on"),
        help="Show the one-click demo account buttons on the sign-in page. Turn off for any public deployment.",
    )
    args = parser.parse_args()

    initialize_database(reset=args.reset)
    server = ThreadingHTTPServer((args.host, args.port), EduStreamHandler)
    if args.secure_cookies == "auto":
        server.secure_cookies = not is_loopback_host(args.host)
    else:
        server.secure_cookies = args.secure_cookies == "on"
    server.demo_logins = args.demo_logins == "on"
    if server.secure_cookies:
        print("Session cookies are marked Secure: serve the site over HTTPS (for example behind a TLS proxy).")
    print(f"EduStream is running at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop the server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
