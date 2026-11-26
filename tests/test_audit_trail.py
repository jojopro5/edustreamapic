"""T4 audit trail and T1 cross-site request tests. IDs: T4-AU-nn and T1-CS-nn."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

import server
from support import LiveServerTestCase


class AuditTrailTests(LiveServerTestCase):
    db_name = "edustream-audit.db"

    def test_T4_AU_01_every_response_carries_a_request_id(self):
        anonymous = self.client()
        self.request(anonymous, "/api/session")
        generated = self.last_headers["X-Request-ID"]
        self.assertRegex(generated, r"^[0-9a-f]{16}$")
        self.request(anonymous, "/api/session", headers={"X-Request-ID": "integration-run-0001"})
        self.assertEqual(self.last_headers["X-Request-ID"], "integration-run-0001")
        self.request(anonymous, "/api/session", headers={"X-Request-ID": "bad id <script>"})
        self.assertRegex(self.last_headers["X-Request-ID"], r"^[0-9a-f]{16}$")

    def test_T4_AU_02_events_from_one_request_share_its_correlation_id(self):
        learner = self.login("learner")
        self.request(learner, "/api/access/3", expected=403, headers={"X-Request-ID": "trace-denied-access-3"})
        events = [event for event in self.audit() if event["correlation_id"] == "trace-denied-access-3"]
        self.assertEqual([event["event_type"] for event in events], ["access_denied"])
        self.assertEqual(events[0]["outcome"], "denied")
        self.request(learner, "/api/access/1", headers={"X-Request-ID": "trace-allowed-access-1"})
        allowed = [event for event in self.audit() if event["correlation_id"] == "trace-allowed-access-1"]
        self.assertEqual([(event["event_type"], event["outcome"]) for event in allowed], [("content_accessed", "success")])

    def test_T4_AU_03_failed_and_throttled_sign_ins_are_recorded_without_secrets(self):
        client = self.client()
        for _ in range(server.LOGIN_MAX_FAILURES_PER_ACCOUNT):
            self.request(client, "/api/login", "POST", {"email": "learner@edustream.local", "password": "Wrong-Guess-1"}, 401)
        self.request(client, "/api/login", "POST", {"email": "learner@edustream.local", "password": "Learn123!"}, 429)
        self.request(client, "/api/login", "POST", {"email": "nobody@edustream.local", "password": "x"}, 401)
        failed = self.audit("login_failed")
        self.assertGreaterEqual(len(failed), server.LOGIN_MAX_FAILURES_PER_ACCOUNT + 1)
        self.assertTrue(all(event["outcome"] == "failure" for event in failed))
        throttled = self.audit("login_throttled")
        self.assertEqual(throttled[-1]["outcome"], "denied")
        for event in failed + throttled:
            self.assertNotIn("@", event["details"])
            self.assertNotIn("Wrong-Guess-1", event["details"])
            self.assertNotIn("Learn123!", event["details"])
        self.assertIn(server.pseudonym("learner@edustream.local"), failed[0]["details"])

    def test_T4_AU_04_wrong_role_requests_are_recorded_as_denied(self):
        learner = self.login("learner")
        self.request(learner, "/api/admin/audit", expected=403)
        self.request(learner, "/api/content", "POST", {"title": "x"}, 403)
        denied = self.audit("permission_denied")
        self.assertGreaterEqual(len(denied), 2)
        self.assertTrue(all(event["outcome"] == "denied" and event["correlation_id"] for event in denied))
        self.assertIn("needs admin, account is learner", denied[-2]["details"])

    def test_T4_AU_05_logout_is_recorded(self):
        learner = self.login("learner")
        before = len(self.audit("logout"))
        self.request(learner, "/api/logout", "POST", {})
        self.assertEqual(len(self.audit("logout")), before + 1)

    def test_T4_AU_06_admin_can_filter_the_audit_log(self):
        admin, learner = self.login("admin"), self.login("learner")
        self.request(learner, "/api/access/3", expected=403, headers={"X-Request-ID": "trace-filter-check"})
        by_id = self.request(admin, "/api/admin/audit?correlation_id=trace-filter-check")["events"]
        self.assertEqual([event["event_type"] for event in by_id], ["access_denied"])
        denied = self.request(admin, "/api/admin/audit?outcome=denied")["events"]
        self.assertTrue(denied and all(event["outcome"] == "denied" for event in denied))
        logins = self.request(admin, "/api/admin/audit?event_type=login")
        self.assertTrue(all(event["event_type"] == "login" for event in logins["events"]))
        self.assertIn("login", logins["event_types"])
        self.request(admin, "/api/admin/audit?outcome=maybe", expected=400)
        self.request(admin, "/api/admin/audit?event_type=login'--", expected=400)
        self.request(admin, "/api/admin/audit?correlation_id=x", expected=400)

    def test_T4_AU_07_older_databases_gain_the_new_audit_columns(self):
        with tempfile.TemporaryDirectory() as folder:
            old_path = Path(folder) / "legacy.db"
            legacy = sqlite3.connect(old_path)
            legacy.execute("CREATE TABLE audit_events (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, event_type TEXT NOT NULL, details TEXT NOT NULL, created_at TEXT NOT NULL)")
            legacy.execute("INSERT INTO audit_events (user_id, event_type, details, created_at) VALUES (NULL, 'login', 'old', '2026-01-01T00:00:00+00:00')")
            legacy.commit()
            legacy.close()
            saved = server.DB_PATH
            try:
                server.DB_PATH = old_path
                server.initialize_database()
                with server.connect_db() as connection:
                    row = connection.execute("SELECT details, outcome, correlation_id FROM audit_events WHERE details = 'old'").fetchone()
                self.assertEqual(tuple(row), ("old", "success", None))
            finally:
                server.DB_PATH = saved

    # Cross-site request forgery checks (Student 1 session handling)

    def test_T1_CS_01_cross_site_posts_are_blocked(self):
        learner = self.login("learner")
        evil = {"Origin": "https://evil.example"}
        self.request(learner, "/api/progress", "POST", {"item_id": 1, "progress": 99}, 403, headers=evil)
        self.request(learner, "/api/progress", "POST", {"item_id": 1, "progress": 99}, 403, headers={"Origin": "null"})
        form = b"item_id=1&progress=99"
        self.raw(learner, "/api/progress", "POST", form, {"Content-Type": "application/x-www-form-urlencoded"}, 403)
        self.raw(learner, "/api/progress", "POST", b'{"item_id": 1, "progress": 99}', {"Content-Type": "text/plain"}, 403)
        blocked = self.audit("request_blocked")
        self.assertGreaterEqual(len(blocked), 4)
        self.assertTrue(all(event["outcome"] == "denied" for event in blocked))
        with server.connect_db() as connection:
            progress = connection.execute("SELECT progress_percent FROM progress WHERE user_id = 1 AND learning_item_id = 1").fetchone()[0]
        self.assertNotEqual(progress, 99)

    def test_T1_CS_02_same_site_posts_still_work(self):
        learner = self.login("learner")
        self.request(learner, "/api/progress", "POST", {"item_id": 1, "progress": 70}, headers={"Origin": self.base_url})
        self.request(learner, "/api/progress", "POST", {"item_id": 1, "progress": 71})


if __name__ == "__main__":
    unittest.main()
