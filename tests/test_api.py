import http.cookiejar
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import server


class EduStreamApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        server.DB_PATH = Path(cls.temp_dir.name) / "edustream-test.db"
        server.SESSIONS.clear()
        server.initialize_database(reset=True)
        cls.httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.EduStreamHandler)
        cls.base_url = f"http://127.0.0.1:{cls.httpd.server_port}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=3)
        cls.temp_dir.cleanup()

    def client(self):
        jar = http.cookiejar.CookieJar()
        return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def request(self, client, path, method="GET", payload=None, expected=200):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            response = client.open(request, timeout=5)
            status = response.status
            body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            status = error.code
            body = json.loads(error.read().decode("utf-8"))
        self.assertEqual(status, expected, body)
        return body

    def login(self, role):
        credentials = {
            "learner": ("learner@edustream.local", "Learn123!"),
            "educator": ("educator@edustream.local", "Teach123!"),
            "admin": ("admin@edustream.local", "Admin123!"),
        }
        client = self.client()
        email, password = credentials[role]
        body = self.request(client, "/api/login", "POST", {"email": email, "password": password})
        self.assertEqual(body["user"]["role"], role)
        return client

    def test_learner_dashboard_and_entitlements(self):
        client = self.login("learner")
        dashboard = self.request(client, "/api/dashboard")
        self.assertEqual(dashboard["role"], "learner")
        self.assertEqual(dashboard["subscription"]["plan_code"], "starter")
        self.assertTrue(any(item["entitled"] for item in dashboard["items"]))
        self.assertTrue(any(not item["entitled"] for item in dashboard["items"]))

    def test_locked_content_is_denied_then_unlocked_by_plus_plan(self):
        client = self.login("learner")
        dashboard = self.request(client, "/api/dashboard")
        locked = next(item for item in dashboard["items"] if not item["entitled"])
        denied = self.request(client, f"/api/access/{locked['id']}", expected=403)
        self.assertIn("not included", denied["error"])

        plus = next(plan for plan in dashboard["plans"] if plan["code"] == "plus")
        changed = self.request(client, "/api/subscription", "POST", {"plan_id": plus["id"]})
        self.assertIn("Plus", changed["message"])
        allowed = self.request(client, f"/api/access/{locked['id']}")
        self.assertEqual(allowed["item"]["id"], locked["id"])

    def test_progress_requires_entitlement(self):
        client = self.login("learner")
        dashboard = self.request(client, "/api/dashboard")
        included = next(item for item in dashboard["items"] if item["entitled"])
        updated = self.request(client, "/api/progress", "POST", {"item_id": included["id"], "progress": 90})
        self.assertEqual(updated["progress"], 90)

    def test_educator_submission_and_admin_approval(self):
        educator = self.login("educator")
        created = self.request(
            educator,
            "/api/content",
            "POST",
            {
                "title": "Responsible Data Sharing",
                "category": "Privacy",
                "description": "A practical module about sharing learning data safely and with clear permission.",
                "content_type": "course",
                "duration_minutes": 40,
            },
        )
        item_id = created["item_id"]
        educator_dashboard = self.request(educator, "/api/dashboard")
        item = next(item for item in educator_dashboard["items"] if item["id"] == item_id)
        self.assertEqual(item["status"], "pending")

        admin = self.login("admin")
        admin_dashboard = self.request(admin, "/api/dashboard")
        self.assertTrue(any(item["id"] == item_id for item in admin_dashboard["pending_items"]))
        self.request(admin, f"/api/admin/content/{item_id}/review", "POST", {"decision": "approved"})
        refreshed = self.request(admin, "/api/dashboard")
        self.assertFalse(any(item["id"] == item_id for item in refreshed["pending_items"]))

    def test_role_protection(self):
        educator = self.login("educator")
        denied = self.request(educator, "/api/subscription", "POST", {"plan_id": 1}, expected=403)
        self.assertIn("permission", denied["error"].lower())

    def quiz_answers(self, correct=True):
        answers = {}
        for question in server.QUIZZES[1]["questions"]:
            answer = question["correct_option_id"]
            if not correct:
                answer = next(option["id"] for option in question["options"] if option["id"] != answer)
            answers[question["id"]] = answer
        return answers

    def quiz_attempt_count(self):
        with server.connect_db() as connection:
            return connection.execute("SELECT COUNT(*) FROM quiz_attempts").fetchone()[0]

    def test_quiz_questions_hide_grading_keys(self):
        client = self.login("learner")
        response = self.request(client, "/api/quiz/1")
        quiz = response["quiz"]
        self.assertEqual(quiz["item_id"], 1)
        self.assertEqual(quiz["pass_percent"], 80)
        self.assertEqual(len(quiz["questions"]), 5)
        for question in quiz["questions"]:
            self.assertEqual(set(question), {"id", "prompt", "options"})
            self.assertGreaterEqual(len(question["options"]), 2)
            self.assertTrue(all(set(option) == {"id", "text"} for option in question["options"]))
        self.assertNotIn("correct_option_id", json.dumps(response))
        self.assertNotIn("explanation", json.dumps(response))

    def test_quiz_results_retake_and_account_isolation(self):
        learner = self.login("learner")
        first = self.request(
            learner, "/api/quiz/1/submit", "POST", {"answers": self.quiz_answers()}
        )["result"]
        self.assertEqual((first["score"], first["correct"], first["total_questions"]), (100, 5, 5))
        self.assertTrue(first["passed"])
        self.assertEqual(len(first["feedback"]), 5)
        self.assertTrue(all(feedback["correct"] for feedback in first["feedback"]))
        saved = self.request(learner, "/api/quiz/1")["last_attempt"]
        self.assertEqual(saved["score"], 100)

        second = self.request(
            learner, "/api/quiz/1/submit", "POST", {"answers": self.quiz_answers(correct=False)}
        )["result"]
        self.assertEqual((second["score"], second["correct"]), (0, 0))
        self.assertFalse(second["passed"])
        self.assertNotEqual(second["attempt_id"], first["attempt_id"])
        self.assertTrue(all(not feedback["correct"] for feedback in second["feedback"]))
        self.assertTrue(all(feedback["correct_option_id"] for feedback in second["feedback"]))
        self.assertEqual(self.request(learner, "/api/quiz/1")["last_attempt"]["score"], 0)

        # Give a separate learner the same plan, without copying any quiz attempts.
        with server.connect_db() as connection:
            source_user = connection.execute(
                "SELECT id FROM users WHERE email = ?", ("learner@edustream.local",)
            ).fetchone()[0]
            cursor = connection.execute(
                """
                INSERT INTO users (full_name, email, password_salt, password_hash, role, created_at)
                SELECT ?, ?, password_salt, password_hash, 'learner', ?
                FROM users WHERE id = ?
                """,
                ("Second Learner", "second-learner@edustream.local", server.iso_now(), source_user),
            )
            second_user = cursor.lastrowid
            connection.execute(
                """
                INSERT INTO subscriptions (user_id, plan_id, status, start_date, end_date, created_at)
                SELECT ?, plan_id, status, start_date, end_date, created_at
                FROM subscriptions WHERE user_id = ? AND status = 'active'
                ORDER BY id DESC LIMIT 1
                """,
                (second_user, source_user),
            )
        other = self.client()
        self.request(
            other, "/api/login", "POST",
            {"email": "second-learner@edustream.local", "password": "Learn123!"},
        )
        self.assertIsNone(self.request(other, "/api/quiz/1")["last_attempt"])

    def test_quiz_rejects_incomplete_and_invalid_answers_without_saving(self):
        learner = self.login("learner")
        complete = self.quiz_answers()
        missing = dict(complete)
        missing.pop(next(iter(missing)))
        invalid = dict(complete)
        invalid[next(iter(invalid))] = "not-a-real-option"
        unexpected = {**complete, "unknown-question": "a"}
        initial_count = self.quiz_attempt_count()
        for answers in (missing, invalid, unexpected):
            with self.subTest(answers=answers):
                self.request(learner, "/api/quiz/1/submit", "POST", {"answers": answers}, expected=400)
                self.assertEqual(self.quiz_attempt_count(), initial_count)

    def test_quiz_requires_login_learner_role_and_active_entitlement(self):
        payload = {"answers": self.quiz_answers()}
        anonymous = self.client()
        self.request(anonymous, "/api/quiz/1", expected=401)
        self.request(anonymous, "/api/quiz/1/submit", "POST", payload, expected=401)
        for role in ("educator", "admin"):
            client = self.login(role)
            self.request(client, "/api/quiz/1", expected=403)
            self.request(client, "/api/quiz/1/submit", "POST", payload, expected=403)

        learner = self.login("learner")
        with server.connect_db() as connection:
            learner_id = connection.execute(
                "SELECT id FROM users WHERE email = ?", ("learner@edustream.local",)
            ).fetchone()[0]
            dates = connection.execute(
                "SELECT id, end_date FROM subscriptions WHERE user_id = ? AND status = 'active'",
                (learner_id,),
            ).fetchall()
            connection.execute(
                "UPDATE subscriptions SET end_date = ? WHERE user_id = ? AND status = 'active'",
                ("2000-01-01", learner_id),
            )
        try:
            self.request(learner, "/api/quiz/1", expected=403)
            self.request(learner, "/api/quiz/1/submit", "POST", payload, expected=403)
        finally:
            with server.connect_db() as connection:
                connection.executemany(
                    "UPDATE subscriptions SET end_date = ? WHERE id = ?",
                    [(row["end_date"], row["id"]) for row in dates],
                )

    def test_quiz_unknown_item_is_not_found(self):
        learner = self.login("learner")
        self.request(learner, "/api/quiz/99999", expected=404)
        self.request(
            learner, "/api/quiz/99999/submit", "POST", {"answers": self.quiz_answers()}, expected=404
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
