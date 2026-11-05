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
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parent
STATIC_ROOT = ROOT / "static"
DATA_ROOT = ROOT / "data"
DB_PATH = DATA_ROOT / "edustream.db"
SCHEMA_PATH = ROOT / "database" / "schema.sql"

SESSION_COOKIE = "edustream_session"
SESSION_TTL = timedelta(hours=8)
SESSIONS: dict[str, dict] = {}


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
        seed_database(connection)


def record_audit(connection: sqlite3.Connection, user_id: int | None, event_type: str, details: str) -> None:
    connection.execute(
        "INSERT INTO audit_events (user_id, event_type, details, created_at) VALUES (?, ?, ?, ?)",
        (user_id, event_type, details[:500], iso_now()),
    )


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


def has_entitlement(connection: sqlite3.Connection, user_id: int, item_id: int) -> bool:
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


def row_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


def clean_sessions() -> None:
    now = utc_now()
    expired = [token for token, session in SESSIONS.items() if session["expires"] <= now]
    for token in expired:
        SESSIONS.pop(token, None)


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

    def _json(self, payload: dict | list, status: int = 200, cookies: list[str] | None = None) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._security_headers(api=True)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
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
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("Request body must be valid JSON")

    def _session_token(self) -> str | None:
        cookie_header = self.headers.get("Cookie")
        if not cookie_header:
            return None
        cookie = SimpleCookie()
        cookie.load(cookie_header)
        morsel = cookie.get(SESSION_COOKIE)
        return morsel.value if morsel else None

    def _current_user(self) -> dict | None:
        clean_sessions()
        token = self._session_token()
        session = SESSIONS.get(token or "")
        if not session:
            return None
        with connect_db() as connection:
            user = connection.execute(
                "SELECT id, full_name, email, role FROM users WHERE id = ? AND is_active = 1",
                (session["user_id"],),
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

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if not path.startswith("/api/"):
            self._serve_static(parsed.path)
            return

        if path == "/api/session":
            user = self._current_user()
            with connect_db() as connection:
                plans = [dict(row) for row in connection.execute("SELECT * FROM plans ORDER BY price_monthly")]
            self._json({"ok": True, "authenticated": bool(user), "user": user, "plans": plans})
            return

        if path == "/api/dashboard":
            user = self._require_user()
            if not user:
                return
            self._json({"ok": True, **self._dashboard(user)})
            return

        match = re.fullmatch(r"/api/access/(\d+)", path)
        if match:
            user = self._require_user({"learner"})
            if not user:
                return
            item_id = int(match.group(1))
            with connect_db() as connection:
                item = connection.execute(
                    "SELECT id, title, category, description, content_type, duration_minutes, status FROM learning_items WHERE id = ?",
                    (item_id,),
                ).fetchone()
                if not item or not has_entitlement(connection, user["id"], item_id):
                    record_audit(connection, user["id"], "access_denied", f"Learning item {item_id}")
                    connection.commit()
                    self._error("This learning item is not included in your active subscription.", HTTPStatus.FORBIDDEN)
                    return
                record_audit(connection, user["id"], "content_accessed", f"Learning item {item_id}")
                connection.commit()
            self._json(
                {
                    "ok": True,
                    "item": dict(item),
                    "lesson": {
                        "heading": "Lesson available",
                        "body": "Your entitlement was verified successfully. This prototype can now deliver the protected learning material.",
                    },
                }
            )
            return

        self._error("API endpoint not found.", HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        try:
            if path == "/api/login":
                self._login(self._body())
                return
            if path == "/api/logout":
                token = self._session_token()
                if token:
                    SESSIONS.pop(token, None)
                self._json(
                    {"ok": True},
                    cookies=[f"{SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"],
                )
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
            if path == "/api/content":
                user = self._require_user({"educator", "admin"})
                if user:
                    self._create_content(user, self._body())
                return
            match = re.fullmatch(r"/api/admin/content/(\d+)/review", path)
            if match:
                user = self._require_user({"admin"})
                if user:
                    self._review_content(user, int(match.group(1)), self._body())
                return
            self._error("API endpoint not found.", HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self._error(str(exc), HTTPStatus.BAD_REQUEST)

    def _login(self, body: dict) -> None:
        email = str(body.get("email", "")).strip().lower()
        password = str(body.get("password", ""))
        if not email or not password:
            raise ValueError("Email and password are required.")
        with connect_db() as connection:
            user = connection.execute(
                "SELECT * FROM users WHERE email = ? AND is_active = 1",
                (email,),
            ).fetchone()
            if not user or not verify_password(password, user["password_salt"], user["password_hash"]):
                self._error("The email or password is incorrect.", HTTPStatus.UNAUTHORIZED)
                return
            token = secrets.token_urlsafe(32)
            SESSIONS[token] = {"user_id": user["id"], "expires": utc_now() + SESSION_TTL}
            record_audit(connection, user["id"], "login", "Successful sign in")
            connection.commit()
        self._json(
            {"ok": True, "user": {"id": user["id"], "full_name": user["full_name"], "email": user["email"], "role": user["role"]}},
            cookies=[f"{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={int(SESSION_TTL.total_seconds())}"],
        )

    def _dashboard(self, user: dict) -> dict:
        with connect_db() as connection:
            plans = [dict(row) for row in connection.execute("SELECT * FROM plans ORDER BY price_monthly")]
            if user["role"] == "learner":
                subscription = active_subscription(connection, user["id"])
                plan_id = subscription["plan_id"] if subscription else -1
                items = [
                    dict(row)
                    for row in connection.execute(
                        """
                        SELECT li.id, li.title, li.category, li.description, li.content_type,
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
                ]
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
                        "completed": sum(1 for item in entitled if item["progress_percent"] == 100),
                        "average_progress": average_progress,
                        "locked": sum(1 for item in items if not item["entitled"]),
                    },
                }

            if user["role"] == "educator":
                items = [
                    dict(row)
                    for row in connection.execute(
                        """
                        SELECT id, title, category, description, content_type, duration_minutes, status, created_at
                        FROM learning_items WHERE created_by = ? ORDER BY id DESC
                        """,
                        (user["id"],),
                    )
                ]
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
                    SELECT li.id, li.title, li.category, li.description, li.content_type,
                           li.duration_minutes, li.status, li.created_at, u.full_name AS educator_name
                    FROM learning_items li
                    JOIN users u ON u.id = li.created_by
                    WHERE li.status = 'pending'
                    ORDER BY li.created_at
                    """
                )
            ]
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
                "plans": plans,
                "stats": {
                    "learners": counts.get("learner", 0),
                    "educators": counts.get("educator", 0),
                    "active_subscriptions": active_count,
                    "approved_content": approved_count,
                    "pending_content": len(pending_items),
                },
            }

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
        self._json({"ok": True, "message": "Progress updated.", "progress": progress})

    def _change_subscription(self, user: dict, body: dict) -> None:
        try:
            plan_id = int(body.get("plan_id"))
        except (TypeError, ValueError):
            raise ValueError("Select a valid subscription plan.")
        with connect_db() as connection:
            plan = connection.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
            if not plan:
                raise ValueError("The selected subscription plan does not exist.")
            connection.execute(
                "UPDATE subscriptions SET status = 'cancelled' WHERE user_id = ? AND status = 'active'",
                (user["id"],),
            )
            start_date = utc_now().date()
            end_date = start_date + timedelta(days=30)
            cursor = connection.execute(
                """
                INSERT INTO subscriptions (user_id, plan_id, status, start_date, end_date, created_at)
                VALUES (?, ?, 'active', ?, ?, ?)
                """,
                (user["id"], plan_id, start_date.isoformat(), end_date.isoformat(), iso_now()),
            )
            connection.execute(
                "INSERT INTO payments (user_id, subscription_id, amount, status, paid_at) VALUES (?, ?, ?, 'paid', ?)",
                (user["id"], cursor.lastrowid, plan["price_monthly"], iso_now()),
            )
            record_audit(connection, user["id"], "subscription_changed", f"Plan changed to {plan['name']}")
            connection.commit()
        self._json({"ok": True, "message": f"Your {plan['name']} plan is now active."})

    def _create_content(self, user: dict, body: dict) -> None:
        title = str(body.get("title", "")).strip()
        category = str(body.get("category", "")).strip()
        description = str(body.get("description", "")).strip()
        content_type = str(body.get("content_type", "course")).strip().lower()
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
        if content_type not in {"course", "video", "article", "quiz", "workshop"}:
            raise ValueError("Select a supported content type.")
        if not 5 <= duration <= 600:
            raise ValueError("Duration must be between 5 and 600 minutes.")
        status = "approved" if user["role"] == "admin" else "pending"
        with connect_db() as connection:
            cursor = connection.execute(
                """
                INSERT INTO learning_items
                    (title, category, description, content_type, duration_minutes, created_by, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (title, category, description, content_type, duration, user["id"], status, iso_now()),
            )
            record_audit(connection, user["id"], "content_created", f"Learning item {cursor.lastrowid}: {title} ({status})")
            connection.commit()
        self._json({"ok": True, "message": "Content submitted for approval." if status == "pending" else "Content published.", "item_id": cursor.lastrowid})

    def _review_content(self, user: dict, item_id: int, body: dict) -> None:
        decision = str(body.get("decision", "")).lower()
        if decision not in {"approved", "rejected"}:
            raise ValueError("Decision must be approved or rejected.")
        with connect_db() as connection:
            item = connection.execute("SELECT id, title FROM learning_items WHERE id = ?", (item_id,)).fetchone()
            if not item:
                self._error("Learning item was not found.", HTTPStatus.NOT_FOUND)
                return
            connection.execute("UPDATE learning_items SET status = ? WHERE id = ?", (decision, item_id))
            if decision == "approved":
                for row in connection.execute("SELECT id FROM plans WHERE code IN ('plus', 'team')"):
                    connection.execute(
                        "INSERT OR IGNORE INTO plan_entitlements (plan_id, learning_item_id) VALUES (?, ?)",
                        (row["id"], item_id),
                    )
            record_audit(connection, user["id"], "content_reviewed", f"{item['title']}: {decision}")
            connection.commit()
        self._json({"ok": True, "message": f"Content {decision}."})


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the EduStream prototype server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    parser.add_argument("--reset", action="store_true", help="Reset the prototype database")
    args = parser.parse_args()

    initialize_database(reset=args.reset)
    server = ThreadingHTTPServer((args.host, args.port), EduStreamHandler)
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
