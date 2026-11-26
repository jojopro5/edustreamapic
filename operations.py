"""Operations summary and seeded problems for the admin view (Student 4, T4).

``summary()`` builds the admin Operations view: a small analytics summary and a
list of open issues detected from the audit log and data. Every issue names
the audit event type that shows it, so the admin can trace it in Audit reports.

``seed_problem()`` (CLI: ``python operations.py seed-problem --kind ...``) plants
a reproducible problem in the synthetic demo data so it can be traced from
event to admin action and fixed:

- ``payment``: a declined renewal for the demo learner, the shape of a real
  failed card payment (fixed by renewing with the approving test card).
- ``access``: a burst of denied requests from the demo learner, the shape of
  someone probing for content outside their plan (reviewed in the audit log).
- ``content``: a published item whose description hides a script tag and an
  off-site link (fixed with an admin takedown).

Each seeding writes a ``problem_seeded`` audit event so the demo is transparent.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

DENIED_BURST_THRESHOLD = 5
STALE_PENDING_DAYS = 7
SEED_KINDS = ("payment", "access", "content")
DEMO_LEARNER = "learner@edustream.local"
SUSPICIOUS_MARKERS = ("<script", "javascript:", "onerror=", "http://", "https://")


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _since(days: float) -> str:
    return (_now() - timedelta(days=days)).isoformat()


def analytics(connection: sqlite3.Connection) -> dict:
    plans = [dict(row) for row in connection.execute(
        """
        SELECT p.name AS plan, COUNT(s.id) AS active_subscriptions
        FROM plans p
        LEFT JOIN subscriptions s
          ON s.plan_id = p.id AND s.status = 'active' AND date(s.end_date) >= date('now')
        GROUP BY p.id ORDER BY p.price_monthly
        """
    )]
    payments = {row["status"]: {"count": row["count"], "amount": round(row["amount"] or 0, 2)} for row in connection.execute(
        "SELECT status, COUNT(*) AS count, SUM(amount) AS amount FROM payments WHERE paid_at >= ? GROUP BY status",
        (_since(30),),
    )}
    courses = [dict(row) for row in connection.execute(
        """
        SELECT li.id, li.title,
               COUNT(DISTINCT p.user_id) AS learners_started,
               ROUND(AVG(p.progress_percent)) AS average_progress,
               (SELECT COUNT(DISTINCT a.user_id) FROM assessment_attempts a
                 WHERE a.learning_item_id = li.id AND a.kind = 'final' AND a.status = 'submitted' AND a.score >= 80) AS finals_passed
        FROM learning_items li
        LEFT JOIN progress p ON p.learning_item_id = li.id
        WHERE li.status = 'approved'
        GROUP BY li.id ORDER BY li.id
        """
    )]
    denied = [dict(row) for row in connection.execute(
        """
        SELECT event_type, COUNT(*) AS count FROM audit_events
        WHERE outcome = 'denied' AND created_at >= ?
        GROUP BY event_type ORDER BY count DESC
        """,
        (_since(7),),
    )]
    return {"plans": plans, "payments_30_days": payments, "courses": courses, "denied_7_days": denied}


def open_issues(connection: sqlite3.Connection) -> list[dict]:
    issues: list[dict] = []
    for row in connection.execute(
        """
        SELECT pay.id, pay.amount, pay.paid_at, u.full_name, pl.name AS plan
        FROM payments pay
        JOIN users u ON u.id = pay.user_id
        JOIN subscriptions s ON s.id = pay.subscription_id
        JOIN plans pl ON pl.id = s.plan_id
        WHERE pay.status = 'failed' AND pay.paid_at >= ?
          AND NOT EXISTS (
              SELECT 1 FROM payments later
              WHERE later.user_id = pay.user_id AND later.status = 'paid' AND later.id > pay.id
          )
        ORDER BY pay.id DESC
        """,
        (_since(7),),
    ):
        issues.append({
            "kind": "payment_failed", "severity": "high", "event_type": "payment_failed",
            "title": f"Failed payment: {row['full_name']}",
            "detail": f"{row['plan']} payment of ${row['amount']:.2f} was declined on {row['paid_at'][:10]} and no payment has succeeded since.",
            "action": "Ask the learner to renew with a working card, or check the billing simulation.",
        })
    for row in connection.execute(
        """
        SELECT ae.user_id, COALESCE(u.full_name, 'Unknown account') AS name, COUNT(*) AS count
        FROM audit_events ae LEFT JOIN users u ON u.id = ae.user_id
        WHERE ae.outcome = 'denied' AND ae.created_at >= ? AND ae.user_id IS NOT NULL
        GROUP BY ae.user_id HAVING COUNT(*) >= ?
        ORDER BY count DESC
        """,
        (_since(1), DENIED_BURST_THRESHOLD),
    ):
        issues.append({
            "kind": "denied_burst", "severity": "medium", "event_type": "", "user_id": row["user_id"],
            "title": f"Repeated denied requests: {row['name']}",
            "detail": f"{row['count']} requests from this account were denied in the last 24 hours.",
            "action": "Review the account's events; deactivate it if the activity is not explained.",
        })
    for row in connection.execute("SELECT id, title, description FROM learning_items WHERE status = 'approved'"):
        text = (row["title"] + " " + row["description"]).lower()
        if any(marker in text for marker in SUSPICIOUS_MARKERS):
            issues.append({
                "kind": "suspicious_content", "severity": "high", "event_type": "content_created", "item_id": row["id"],
                "title": f"Published item needs review: {row['title']}",
                "detail": "Its title or description contains markup or an off-site link. It is shown to learners as plain text, but it should not be published.",
                "action": "Take the item down with a reason, then ask the educator to resubmit.",
            })
    for event_type, title, action in (
        ("backup_verify_failed", "A backup failed verification", "Do not restore it. Take a fresh backup and investigate who changed the file."),
        ("backup_restore_refused", "A restore was refused", "Check the backup's problems in Backup & recovery."),
        ("content_file_integrity_failed", "A course file failed its integrity check", "Take the item down and ask the educator to upload the file again."),
    ):
        count = connection.execute(
            "SELECT COUNT(*) FROM audit_events WHERE event_type = ? AND created_at >= ?", (event_type, _since(7))
        ).fetchone()[0]
        if count:
            issues.append({
                "kind": event_type, "severity": "high", "event_type": event_type,
                "title": title, "detail": f"{count} in the last 7 days.", "action": action,
            })
    stale = connection.execute(
        "SELECT COUNT(*) FROM learning_items WHERE status = 'pending' AND created_at < ?", (_since(STALE_PENDING_DAYS),)
    ).fetchone()[0]
    if stale:
        issues.append({
            "kind": "stale_pending", "severity": "low", "event_type": "content_created",
            "title": "Submissions waiting more than a week",
            "detail": f"{stale} pending item(s) older than {STALE_PENDING_DAYS} days.",
            "action": "Review them in the approval queue.",
        })
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(issues, key=lambda issue: order[issue["severity"]])


def summary(connection: sqlite3.Connection) -> dict:
    return {"analytics": analytics(connection), "issues": open_issues(connection)}


def _record(connection: sqlite3.Connection, user_id, event_type: str, details: str, outcome: str) -> None:
    connection.execute(
        "INSERT INTO audit_events (user_id, event_type, details, created_at, outcome, correlation_id) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, event_type, details, _now().isoformat(), outcome, "seeded-" + event_type[:20]),
    )


def seed_problem(db_path: Path, kind: str) -> str:
    if kind not in SEED_KINDS:
        raise ValueError(f"kind must be one of {', '.join(SEED_KINDS)}")
    connection = sqlite3.connect(db_path, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        learner = connection.execute("SELECT id FROM users WHERE email = ?", (DEMO_LEARNER,)).fetchone()
        if not learner:
            raise ValueError("The demo learner account is missing; run the server once with --reset first.")
        learner_id = learner["id"]
        now = _now().isoformat()
        if kind == "payment":
            plan = connection.execute("SELECT id, name, price_monthly FROM plans WHERE code = 'starter'").fetchone()
            cursor = connection.execute(
                "INSERT INTO subscriptions (user_id, plan_id, status, start_date, end_date, created_at) VALUES (?, ?, 'cancelled', date('now'), date('now'), ?)",
                (learner_id, plan["id"], now),
            )
            connection.execute(
                "INSERT INTO payments (user_id, subscription_id, amount, status, paid_at) VALUES (?, ?, ?, 'failed', ?)",
                (learner_id, cursor.lastrowid, plan["price_monthly"], now),
            )
            _record(connection, learner_id, "payment_failed", f"Simulated card declined for {plan['name']} (renew); plan unchanged", "failure")
            message = "Seeded a declined Starter renewal for the demo learner."
        elif kind == "access":
            for _ in range(DENIED_BURST_THRESHOLD + 1):
                _record(connection, learner_id, "access_denied", "Learning item 3", "denied")
            message = f"Seeded {DENIED_BURST_THRESHOLD + 1} denied access attempts from the demo learner."
        else:
            educator = connection.execute("SELECT id FROM users WHERE role = 'educator' ORDER BY id LIMIT 1").fetchone()
            cursor = connection.execute(
                """
                INSERT INTO learning_items (title, category, description, content_type, language, duration_minutes, created_by, status, created_at)
                VALUES (?, 'Cybersecurity', ?, 'article', 'en', 15, ?, 'approved', ?)
                """,
                ("Free exam answers", "Click https://answers.example.invalid now <script>alert('x')</script> for the final exam key.", educator["id"], now),
            )
            _record(connection, educator["id"], "content_created", f"Learning item {cursor.lastrowid}: Free exam answers (approved)", "success")
            message = f"Seeded a suspicious published item (id {cursor.lastrowid})."
        _record(connection, None, "problem_seeded", f"kind={kind}: {message}", "success")
        connection.commit()
        return message
    finally:
        connection.close()


def main(argv: list[str] | None = None) -> int:
    import server  # local import so this module stays importable from server.py

    parser = argparse.ArgumentParser(description="EduStream operations tools (synthetic demo data only)")
    sub = parser.add_subparsers(dest="command", required=True)
    seed = sub.add_parser("seed-problem", help="Plant a reproducible problem for the T4 demo")
    seed.add_argument("--kind", choices=SEED_KINDS, required=True)
    args = parser.parse_args(argv)
    server.initialize_database()
    print(seed_problem(server.DB_PATH, args.kind))
    return 0


if __name__ == "__main__":
    sys.exit(main())
