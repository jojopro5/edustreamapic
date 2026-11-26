"""Subscription confirmation, paid-day carry-over, one completion rule, and synthetic thumbnails.

Test IDs:
  T1_SUB_01-05  plan change and renewal need confirmation and keep paid days
  T1_SUB_06-07  the hidden Team plan is not offered, but existing Team learners keep it
  T3_CMP_01-03  the progress message and the Completed counter use one rule
  GEN_SYN_01-02 course guide thumbnails are synthetic files served locally
"""

import http.cookiejar
import json
import re
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import server

ROOT = Path(__file__).resolve().parent.parent


class QuietHandler(server.EduStreamHandler):
    def log_message(self, fmt, *args):
        pass


def reset_auth_state():
    # Works both before and after the login-hardening PR changes these names.
    if hasattr(server, "SESSIONS"):
        server.SESSIONS.clear()
    if hasattr(server, "LOGIN_THROTTLE"):
        server.LOGIN_THROTTLE.reset()


class BillingAndCompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_db_path = server.DB_PATH
        cls.temp_dir = tempfile.TemporaryDirectory()
        server.DB_PATH = Path(cls.temp_dir.name) / "billing-test.db"
        cls.httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        cls.base_url = f"http://127.0.0.1:{cls.httpd.server_port}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=3)
        reset_auth_state()
        server.DB_PATH = cls.original_db_path
        cls.temp_dir.cleanup()

    def setUp(self):
        reset_auth_state()
        server.initialize_database(reset=True)
        self.learner = self.login()
        with server.connect_db() as connection:
            self.learner_id = connection.execute(
                "SELECT id FROM users WHERE email = 'learner@edustream.local'"
            ).fetchone()[0]

    # -- helpers ---------------------------------------------------------

    def request(self, client, path, method="GET", payload=None, expected=200, raw=False):
        request = urllib.request.Request(
            self.base_url + path,
            data=None if payload is None else json.dumps(payload).encode("utf-8"),
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with client.open(request, timeout=8) as response:
                status, headers, data = response.status, response.headers, response.read()
        except urllib.error.HTTPError as error:
            status, headers, data = error.code, error.headers, error.read()
        if raw:
            self.assertEqual(status, expected)
            return headers, data
        body = json.loads(data)
        self.assertEqual(status, expected, body)
        return body

    def login(self):
        client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.request(client, "/api/login", "POST", {"email": "learner@edustream.local", "password": "Learn123!"})
        return client

    def plan(self, code):
        plans = self.request(self.learner, "/api/dashboard")["plans"]
        return next(plan for plan in plans if plan["code"] == code)

    def set_end_date(self, end):
        with server.connect_db() as connection:
            connection.execute(
                "UPDATE subscriptions SET end_date = ? WHERE user_id = ? AND status = 'active'",
                (end.isoformat(), self.learner_id),
            )

    def billing_snapshot(self):
        with server.connect_db() as connection:
            subs = [tuple(row) for row in connection.execute(
                "SELECT id, plan_id, status, start_date, end_date FROM subscriptions WHERE user_id = ? ORDER BY id",
                (self.learner_id,),
            )]
            payments = connection.execute(
                "SELECT COUNT(*) FROM payments WHERE user_id = ?", (self.learner_id,)
            ).fetchone()[0]
        return subs, payments

    def active(self):
        return self.request(self.learner, "/api/dashboard")["subscription"]

    def pass_all_assessments(self, item_id):
        for assessment_id in ("module-1", "module-2", "module-3", "final"):
            attempt = self.request(
                self.learner, f"/api/assessments/{item_id}/start", "POST", {"assessment_id": assessment_id}
            )["attempt"]
            with server.connect_db() as connection:
                questions = json.loads(connection.execute(
                    "SELECT questions_json FROM assessment_attempts WHERE id = ?", (attempt["id"],)
                ).fetchone()["questions_json"])
            answers = {question["id"]: question["correct_option_id"] for question in questions}
            self.request(
                self.learner, f"/api/assessment-attempts/{attempt['id']}/submit", "POST", {"answers": answers}
            )

    # -- T1: subscription changes ---------------------------------------

    def test_T1_SUB_01_unconfirmed_request_returns_quote_and_charges_nothing(self):
        before = self.billing_snapshot()
        plus = self.plan("plus")
        for payload in ({"plan_id": plus["id"]}, {"plan_id": plus["id"], "confirm": "true"}, {"plan_id": plus["id"], "confirm": 1}):
            with self.subTest(payload=payload):
                body = self.request(self.learner, "/api/subscription", "POST", payload)
                self.assertTrue(body["requires_confirmation"])
                self.assertEqual(body["quote"]["action"], "change")
                self.assertEqual(body["quote"]["amount"], plus["price_monthly"])
        self.assertEqual(self.billing_snapshot(), before)
        self.assertEqual(self.active()["plan_code"], "starter")

    def test_T1_SUB_02_renewal_extends_from_current_end_date(self):
        current_end = date.today() + timedelta(days=12)
        self.set_end_date(current_end)
        starter = self.plan("starter")
        quote = self.request(self.learner, "/api/subscription", "POST", {"plan_id": starter["id"]})["quote"]
        self.assertEqual(quote["action"], "renew")
        self.assertEqual(quote["new_end_date"], (current_end + timedelta(days=30)).isoformat())
        _, payments_before = self.billing_snapshot()
        body = self.request(self.learner, "/api/subscription", "POST", {"plan_id": starter["id"], "confirm": True})
        self.assertIn("renewed", body["message"])
        self.assertEqual(self.active()["end_date"], (current_end + timedelta(days=30)).isoformat())
        self.assertEqual(self.billing_snapshot()[1], payments_before + 1)

    def test_T1_SUB_03_plan_change_keeps_paid_days(self):
        current_end = date.today() + timedelta(days=20)
        self.set_end_date(current_end)
        plus = self.plan("plus")
        quote = self.request(self.learner, "/api/subscription", "POST", {"plan_id": plus["id"]})["quote"]
        self.assertGreaterEqual(quote["days_kept"], 19)
        self.request(self.learner, "/api/subscription", "POST", {"plan_id": plus["id"], "confirm": True})
        active = self.active()
        self.assertEqual(active["plan_code"], "plus")
        self.assertEqual(active["end_date"], (current_end + timedelta(days=30)).isoformat())
        with server.connect_db() as connection:
            active_rows = connection.execute(
                "SELECT COUNT(*) FROM subscriptions WHERE user_id = ? AND status = 'active'", (self.learner_id,)
            ).fetchone()[0]
        self.assertEqual(active_rows, 1)

    def test_T1_SUB_04_expired_subscription_starts_from_today(self):
        self.set_end_date(date.today() - timedelta(days=5))
        plus = self.plan("plus")
        quote = self.request(self.learner, "/api/subscription", "POST", {"plan_id": plus["id"]})["quote"]
        self.assertEqual(quote["action"], "subscribe")
        self.assertEqual(quote["days_kept"], 0)
        self.request(self.learner, "/api/subscription", "POST", {"plan_id": plus["id"], "confirm": True})
        self.assertEqual(self.active()["end_date"], (date.today() + timedelta(days=30)).isoformat())

    def test_T1_SUB_05_repeated_renewals_stack_and_are_audited(self):
        starter = self.plan("starter")
        start_end = date.fromisoformat(self.active()["end_date"])
        for _ in range(2):
            self.request(self.learner, "/api/subscription", "POST", {"plan_id": starter["id"], "confirm": True})
        self.assertEqual(self.active()["end_date"], (start_end + timedelta(days=60)).isoformat())
        with server.connect_db() as connection:
            details = [row[0] for row in connection.execute(
                "SELECT details FROM audit_events WHERE event_type = 'subscription_changed' AND user_id = ?",
                (self.learner_id,),
            )]
        self.assertEqual(len(details), 2)
        self.assertTrue(all("access ends" in detail for detail in details))

    def team_plan_id(self):
        with server.connect_db() as connection:
            return connection.execute("SELECT id FROM plans WHERE code = 'team'").fetchone()["id"]

    def test_T1_SUB_06_team_plan_is_hidden_and_cannot_be_bought(self):
        codes = [plan["code"] for plan in self.request(self.learner, "/api/dashboard")["plans"]]
        self.assertEqual(codes, ["starter", "plus"])
        session_codes = [plan["code"] for plan in self.request(self.learner, "/api/session")["plans"]]
        self.assertNotIn("team", session_codes)
        before = self.billing_snapshot()
        for payload in ({"plan_id": self.team_plan_id()}, {"plan_id": self.team_plan_id(), "confirm": True}):
            with self.subTest(payload=payload):
                body = self.request(self.learner, "/api/subscription", "POST", payload, expected=400)
                self.assertIn("no longer offered", body["error"])
        self.assertEqual(self.billing_snapshot(), before)
        self.assertEqual(self.active()["plan_code"], "starter")

    def test_T1_SUB_07_existing_team_learner_still_sees_and_renews_team(self):
        team_id = self.team_plan_id()
        with server.connect_db() as connection:
            connection.execute(
                "UPDATE subscriptions SET plan_id = ? WHERE user_id = ? AND status = 'active'",
                (team_id, self.learner_id),
            )
            connection.commit()
        codes = [plan["code"] for plan in self.request(self.learner, "/api/dashboard")["plans"]]
        self.assertIn("team", codes)
        start_end = date.fromisoformat(self.active()["end_date"])
        self.request(self.learner, "/api/subscription", "POST", {"plan_id": team_id, "confirm": True})
        self.assertEqual(self.active()["plan_code"], "team")
        self.assertEqual(self.active()["end_date"], (start_end + timedelta(days=30)).isoformat())

    # -- T3: one completion rule ----------------------------------------

    def test_T3_CMP_01_slider_at_100_does_not_claim_completion(self):
        body = self.request(self.learner, "/api/progress", "POST", {"item_id": 1, "progress": 100})
        self.assertFalse(body["completed"])
        self.assertNotIn("Course completed", body["message"])
        self.assertIn("4 assessments", body["message"])
        dashboard = self.request(self.learner, "/api/dashboard")
        item = next(entry for entry in dashboard["items"] if entry["id"] == 1)
        self.assertFalse(item["completed"])
        self.assertEqual(dashboard["stats"]["completed"], 0)

    def test_T3_CMP_02_passing_every_assessment_completes_course_everywhere(self):
        self.pass_all_assessments(1)
        dashboard = self.request(self.learner, "/api/dashboard")
        item = next(entry for entry in dashboard["items"] if entry["id"] == 1)
        self.assertTrue(item["completed"])
        self.assertEqual(dashboard["stats"]["completed"], 1)
        body = self.request(self.learner, "/api/progress", "POST", {"item_id": 1, "progress": 100})
        self.assertTrue(body["completed"])
        self.assertIn("Course completed", body["message"])

    def test_T3_CMP_03_counter_matches_items_and_endpoint(self):
        self.pass_all_assessments(2)
        self.request(self.learner, "/api/progress", "POST", {"item_id": 1, "progress": 100})
        dashboard = self.request(self.learner, "/api/dashboard")
        entitled = [item for item in dashboard["items"] if item["entitled"]]
        self.assertEqual(dashboard["stats"]["completed"], sum(bool(item["completed"]) for item in entitled))
        for item in entitled:
            body = self.request(self.learner, "/api/progress", "POST", {"item_id": item["id"], "progress": item["progress_percent"]})
            self.assertEqual(body["completed"], bool(item["completed"]), item["id"])

    # -- Synthetic content ------------------------------------------------

    def test_GEN_SYN_01_guides_use_only_local_synthetic_thumbnails(self):
        guides = (ROOT / "static" / "course-guides.js").read_text(encoding="utf-8")
        thumbnails = re.findall(r'thumbnail:\s*"([^"]+)"', guides)
        self.assertEqual(len(thumbnails), 12)
        self.assertNotIn("ytimg", guides)
        for path in thumbnails:
            self.assertRegex(path, r"^/thumbnails/[a-z0-9-]+\.svg$")
            self.assertTrue((ROOT / "static" / path.lstrip("/")).is_file(), path)
        stored = sorted(p.suffix for p in (ROOT / "static" / "thumbnails").iterdir())
        self.assertEqual(set(stored), {".svg"})

    def test_GEN_SYN_02_thumbnails_are_served_as_svg(self):
        headers, data = self.request(self.learner, "/thumbnails/cyber-basics.svg", raw=True)
        self.assertEqual(headers.get_content_type(), "image/svg+xml")
        self.assertIn(b"EduStream study clip", data)
        self.assertNotIn(b"<script", data)


if __name__ == "__main__":
    unittest.main()
