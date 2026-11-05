import http.cookiejar
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

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
        self.assertEqual([item["id"] for item in dashboard["items"]], [1, 2, 3])
        self.assertEqual([bool(item["entitled"]) for item in dashboard["items"]], [True, True, False])
        self.assertTrue(all(item["has_quiz"] for item in dashboard["items"]))
        self.assertTrue(all(item["quiz_question_count"] >= 5 for item in dashboard["items"]))

    def test_locked_content_is_denied_then_unlocked_by_plus_plan(self):
        client = self.login("learner")
        dashboard = self.request(client, "/api/dashboard")
        locked = next(item for item in dashboard["items"] if not item["entitled"])
        self.assertEqual(locked["id"], 3)
        self.request(client, f"/api/access/{locked['id']}", expected=403)

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

    def test_quiz_sql_and_web_scores_respect_subscription_access(self):
        learner = self.login("learner")
        plans = self.request(learner, "/api/dashboard")["plans"]
        starter = next(plan for plan in plans if plan["code"] == "starter")
        plus = next(plan for plan in plans if plan["code"] == "plus")
        self.request(learner, "/api/subscription", "POST", {"plan_id": starter["id"]})
        sql_quiz = self.request(learner, "/api/quiz/2")["quiz"]
        self.assertEqual(sql_quiz["item_id"], 2)
        self.request(learner, "/api/quiz/3", expected=403)
        self.request(learner, "/api/quiz/3/submit", "POST", {"answers": {}}, expected=403)
        self.request(learner, "/api/subscription", "POST", {"plan_id": plus["id"]})
        for item_id in (2, 3):
            with self.subTest(item_id=item_id):
                quiz = self.request(learner, f"/api/quiz/{item_id}")["quiz"]
                self.assertEqual(quiz["item_id"], item_id)
                self.assertGreaterEqual(len(quiz["questions"]), 5)
                self.assertNotIn("correct_option_id", json.dumps(quiz))
                self.assertNotIn("explanation", json.dumps(quiz))
                answers = {question["id"]: question["correct_option_id"] for question in server.QUIZZES[item_id]["questions"]}
                result = self.request(learner, f"/api/quiz/{item_id}/submit", "POST", {"answers": answers})["result"]
                self.assertEqual(result["score"], 100)
                self.assertEqual(result["correct"], len(quiz["questions"]))
                self.assertTrue(result["passed"])
                self.assertTrue(all(feedback["correct"] for feedback in result["feedback"]))
                self.assertEqual(self.request(learner, f"/api/quiz/{item_id}")["last_attempt"]["score"], 100)

    def test_visibility_hides_courses_without_quizzes_even_for_plus(self):
        learner = self.login("learner")
        dashboard = self.request(learner, "/api/dashboard")
        plus = next(plan for plan in dashboard["plans"] if plan["code"] == "plus")
        self.request(learner, "/api/subscription", "POST", {"plan_id": plus["id"]})
        with server.connect_db() as connection:
            before = [tuple(row) for row in connection.execute("SELECT * FROM progress ORDER BY user_id, learning_item_id")]
            connection.execute("UPDATE learning_items SET status = 'approved' WHERE id = 4")
            connection.execute("INSERT OR IGNORE INTO plan_entitlements (plan_id, learning_item_id) VALUES (?, 4)", (plus["id"],))
        try:
            dashboard = self.request(learner, "/api/dashboard")
            self.assertEqual([item["id"] for item in dashboard["items"]], [1, 2, 3])
            self.assertEqual(dashboard["stats"]["available"], 3)
            self.assertEqual(dashboard["stats"]["locked"], 0)
            self.request(learner, "/api/access/4", expected=403)
            self.request(learner, "/api/progress", "POST", {"item_id": 4, "progress": 100}, expected=403)
            self.request(learner, "/api/quiz/4", expected=404)
            # Even another approved course with a quiz stays outside this release.
            with patch.dict(server.QUIZZES, {4: {**server.QUIZZES[1], "item_id": 4}}):
                self.assertEqual([item["id"] for item in self.request(learner, "/api/dashboard")["items"]], [1, 2, 3])
                self.request(learner, "/api/access/4", expected=403)
                self.request(learner, "/api/quiz/4", expected=403)
        finally:
            with server.connect_db() as connection:
                connection.execute("UPDATE learning_items SET status = 'pending' WHERE id = 4")
                connection.execute("DELETE FROM plan_entitlements WHERE learning_item_id = 4 AND plan_id = ?", (plus["id"],))
        with server.connect_db() as connection:
            after = [tuple(row) for row in connection.execute("SELECT * FROM progress ORDER BY user_id, learning_item_id")]
        self.assertEqual(after, before)
        educator_items = self.request(self.login("educator"), "/api/dashboard")["items"]
        self.assertTrue({1, 2, 3, 4}.issubset({item["id"] for item in educator_items}))

    def test_visibility_hides_indonesian_quiz_and_rejects_cached_actions(self):
        learner = self.login("learner")
        answers = self.quiz_answers()
        initial_attempts = self.quiz_attempt_count()
        with server.connect_db() as connection:
            before = [tuple(row) for row in connection.execute("SELECT * FROM progress ORDER BY user_id, learning_item_id")]
            connection.execute("UPDATE learning_items SET language = 'id' WHERE id = 1")
        try:
            dashboard = self.request(learner, "/api/dashboard")
            self.assertEqual([item["id"] for item in dashboard["items"]], [2, 3])
            entitled = [item for item in dashboard["items"] if item["entitled"]]
            self.assertEqual(dashboard["stats"]["available"], len(entitled))
            self.assertEqual(dashboard["stats"]["completed"], sum(item["progress_percent"] == 100 for item in entitled))
            self.assertEqual(dashboard["stats"]["average_progress"], round(sum(item["progress_percent"] for item in entitled) / len(entitled)))
            self.request(learner, "/api/access/1", expected=403)
            self.request(learner, "/api/progress", "POST", {"item_id": 1, "progress": 100}, expected=403)
            self.request(learner, "/api/quiz/1", expected=403)
            self.request(learner, "/api/quiz/1/submit", "POST", {"answers": answers}, expected=403)
            self.assertEqual(self.quiz_attempt_count(), initial_attempts)
            with server.connect_db() as connection:
                after = [tuple(row) for row in connection.execute("SELECT * FROM progress ORDER BY user_id, learning_item_id")]
            self.assertEqual(after, before)
            educator_items = self.request(self.login("educator"), "/api/dashboard")["items"]
            self.assertTrue(any(item["id"] == 1 for item in educator_items))
        finally:
            with server.connect_db() as connection:
                connection.execute("UPDATE learning_items SET language = 'en' WHERE id = 1")

    def test_visibility_requires_nonempty_quiz_and_approved_status(self):
        learner = self.login("learner")
        with patch.dict(server.QUIZZES, {1: {**server.QUIZZES[1], "questions": []}}):
            self.assertEqual([item["id"] for item in self.request(learner, "/api/dashboard")["items"]], [2, 3])
            self.request(learner, "/api/access/1", expected=403)
            self.request(learner, "/api/quiz/1", expected=404)
            self.request(learner, "/api/quiz/1/submit", "POST", {"answers": {}}, expected=404)
        try:
            for status in ("pending", "rejected"):
                with self.subTest(status=status):
                    with server.connect_db() as connection:
                        connection.execute("UPDATE learning_items SET status = ? WHERE id = 1", (status,))
                    self.assertEqual([item["id"] for item in self.request(learner, "/api/dashboard")["items"]], [2, 3])
                    self.request(learner, "/api/access/1", expected=403)
                    self.request(learner, "/api/quiz/1", expected=403)
        finally:
            with server.connect_db() as connection:
                connection.execute("UPDATE learning_items SET status = 'approved' WHERE id = 1")

    def test_visibility_stats_exclude_hidden_course_progress(self):
        learner = self.login("learner")
        with server.connect_db() as connection:
            learner_id = connection.execute("SELECT id FROM users WHERE email = 'learner@edustream.local'").fetchone()[0]
            previous = connection.execute("SELECT * FROM progress WHERE user_id = ? AND learning_item_id = 4", (learner_id,)).fetchone()
            connection.execute(
                "INSERT INTO progress (user_id, learning_item_id, progress_percent, completed_at, updated_at) VALUES (?, 4, 100, ?, ?) "
                "ON CONFLICT(user_id, learning_item_id) DO UPDATE SET progress_percent = 100",
                (learner_id, server.iso_now(), server.iso_now()),
            )
        try:
            dashboard = self.request(learner, "/api/dashboard")
            entitled = [item for item in dashboard["items"] if item["entitled"]]
            self.assertFalse(any(item["id"] == 4 for item in dashboard["items"]))
            self.assertEqual(dashboard["stats"]["average_progress"], round(sum(item["progress_percent"] for item in entitled) / len(entitled)))
            self.assertEqual(dashboard["stats"]["completed"], sum(item["progress_percent"] == 100 for item in entitled))
        finally:
            with server.connect_db() as connection:
                connection.execute("DELETE FROM progress WHERE user_id = ? AND learning_item_id = 4", (learner_id,))
                if previous:
                    columns = ", ".join(previous.keys())
                    placeholders = ", ".join("?" for _ in previous.keys())
                    connection.execute(f"INSERT INTO progress ({columns}) VALUES ({placeholders})", tuple(previous))

    def test_visibility_content_language_is_saved_and_validated(self):
        educator = self.login("educator")
        payload = {
            "title": "Keamanan Digital Indonesia",
            "category": "Cybersecurity",
            "description": "Materi pembelajaran tentang kata sandi dan keamanan akun untuk siswa.",
            "content_type": "course",
            "duration_minutes": 45,
            "language": "id",
        }
        created = self.request(educator, "/api/content", "POST", payload)
        with server.connect_db() as connection:
            self.assertEqual(connection.execute("SELECT language FROM learning_items WHERE id = ?", (created["item_id"],)).fetchone()[0], "id")
            count = connection.execute("SELECT COUNT(*) FROM learning_items").fetchone()[0]
        self.request(educator, "/api/content", "POST", {**payload, "language": "unsupported"}, expected=400)
        with server.connect_db() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM learning_items").fetchone()[0], count)

    def test_visibility_migrates_legacy_database_without_losing_records(self):
        import sqlite3

        with tempfile.TemporaryDirectory() as directory:
            legacy_path = Path(directory) / "legacy.db"
            with server.connect_db() as source:
                legacy = sqlite3.connect(legacy_path)
                try:
                    source.backup(legacy)
                    legacy.execute("ALTER TABLE learning_items DROP COLUMN language")
                    legacy.commit()
                    before_items = legacy.execute("SELECT id, title, status FROM learning_items ORDER BY id").fetchall()
                    before_progress = legacy.execute("SELECT * FROM progress ORDER BY user_id, learning_item_id").fetchall()
                    before_users = legacy.execute("SELECT COUNT(*) FROM users").fetchone()[0]
                finally:
                    legacy.close()
            with patch.object(server, "DB_PATH", legacy_path):
                server.initialize_database()
                server.initialize_database()  # Restarts must not recreate or duplicate data.
                with server.connect_db() as connection:
                    self.assertEqual([tuple(row) for row in connection.execute("SELECT id, title, status FROM learning_items ORDER BY id")], before_items)
                    self.assertEqual([tuple(row) for row in connection.execute("SELECT * FROM progress ORDER BY user_id, learning_item_id")], before_progress)
                    self.assertEqual(connection.execute("SELECT COUNT(*) FROM users").fetchone()[0], before_users)
                    self.assertTrue(all(row[0] == "en" for row in connection.execute("SELECT language FROM learning_items")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
