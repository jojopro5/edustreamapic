"""Exercise the learner assessment flow through its HTTP API and saved data."""

import http.cookiejar
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import server


class QuietHandler(server.EduStreamHandler):
    def log_message(self, fmt, *args):
        pass


class AssessmentApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_db_path = server.DB_PATH
        cls.temp_dir = tempfile.TemporaryDirectory()
        server.DB_PATH = Path(cls.temp_dir.name) / "assessments-test.db"
        cls.httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        cls.base_url = f"http://127.0.0.1:{cls.httpd.server_port}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=3)
        server.SESSIONS.clear()
        server.DB_PATH = cls.original_db_path
        cls.temp_dir.cleanup()

    def setUp(self):
        server.SESSIONS.clear()
        server.initialize_database(reset=True)

    def client(self):
        return urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )

    def request(self, client, path, method="GET", payload=None, expected=200):
        request = urllib.request.Request(
            self.base_url + path,
            data=None if payload is None else json.dumps(payload).encode("utf-8"),
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with client.open(request, timeout=8) as response:
                status = response.status
                body = json.loads(response.read())
        except urllib.error.HTTPError as error:
            status = error.code
            body = json.loads(error.read())
        self.assertEqual(status, expected, body)
        return body

    def login(self, role="learner", email=None, password=None):
        default_password = {"learner": "Learn123!", "educator": "Teach123!", "admin": "Admin123!"}
        client = self.client()
        self.request(client, "/api/login", "POST", {
            "email": email or f"{role}@edustream.local",
            "password": password or default_password[role],
        })
        return client

    def plus(self, client):
        plans = self.request(client, "/api/dashboard")["plans"]
        plan = next(plan for plan in plans if plan["code"] == "plus")
        self.request(client, "/api/subscription", "POST", {"plan_id": plan["id"]})

    def start(self, client, item_id=1, assessment_id="module-1"):
        return self.request(client, f"/api/assessments/{item_id}/start", "POST", {
            "assessment_id": assessment_id,
        })["attempt"]

    def answers(self, attempt, correct_count=None):
        with server.connect_db() as connection:
            row = connection.execute(
                "SELECT questions_json FROM assessment_attempts WHERE id = ?", (attempt["id"],)
            ).fetchone()
        questions = json.loads(row["questions_json"])
        if correct_count is None:
            correct_count = len(questions)
        answers = {}
        for index, question in enumerate(questions):
            correct = question["correct_option_id"]
            answers[question["id"]] = correct if index < correct_count else next(
                option["id"] for option in question["options"] if option["id"] != correct
            )
        return answers

    def submit(self, client, attempt, correct_count=None):
        return self.request(client, f"/api/assessment-attempts/{attempt['id']}/submit", "POST", {
            "answers": self.answers(attempt, correct_count),
        })["attempt"]

    def count_attempts(self):
        with server.connect_db() as connection:
            return connection.execute("SELECT COUNT(*) FROM assessment_attempts").fetchone()[0]

    def test_overview_and_drafts_hide_answer_keys(self):
        learner = self.login()
        self.plus(learner)
        for item_id in (1, 2, 3):
            with self.subTest(item_id=item_id):
                overview = self.request(learner, f"/api/assessments/{item_id}")
                self.assertEqual(overview["course"]["total_assessments"], 4)
                self.assertEqual(overview["course"]["passed_count"], 0)
                self.assertFalse(overview["course"]["completed"])
                assessments = overview["assessments"]
                self.assertEqual([entry["id"] for entry in assessments], ["module-1", "module-2", "module-3", "final"])
                self.assertEqual([entry["question_count"] for entry in assessments], [8, 8, 8, 12])
                self.assertTrue(assessments[-1]["locked"])
                attempt = self.start(learner, item_id)
                self.assertEqual(attempt["status"], "in_progress")
                self.assertIsNone(attempt["result"])
                self.assertEqual(attempt["question_count"], 8)
                self.assertEqual(len({question["id"] for question in attempt["questions"]}), 8)
                self.assertNotIn("correct_option_id", json.dumps(attempt))
                self.assertNotIn("explanation", json.dumps(attempt))
                for question in attempt["questions"]:
                    self.assertEqual(len(question["options"]), 4)
                    self.assertEqual({option["id"] for option in question["options"]}, {"a", "b", "c", "d"})

    def test_save_resume_and_invalid_answers_preserve_draft(self):
        learner = self.login()
        attempt = self.start(learner)
        question = attempt["questions"][0]
        partial = {question["id"]: question["options"][0]["id"]}
        path = f"/api/assessment-attempts/{attempt['id']}"
        saved = self.request(learner, path + "/save", "POST", {"answers": partial})["attempt"]
        self.assertEqual(saved["answers"], partial)
        another_session = self.login()
        resumed = self.start(another_session)
        self.assertEqual(resumed["id"], attempt["id"])
        self.assertEqual(resumed["answers"], partial)
        self.assertEqual(resumed["questions"], attempt["questions"])
        self.assertEqual(self.count_attempts(), 1)
        for invalid in ({"unknown-question": "a"}, {question["id"]: "z"}, {question["id"]: ["a"]}, []):
            with self.subTest(invalid=invalid):
                self.request(learner, path + "/save", "POST", {"answers": invalid}, expected=400)
                self.assertEqual(self.request(learner, path)["attempt"]["answers"], partial)
        self.request(learner, path + "/submit", "POST", {"answers": partial}, expected=400)
        self.assertEqual(self.request(learner, path)["attempt"]["status"], "in_progress")

    def test_failed_retry_uses_different_questions_and_pass_boundary(self):
        learner = self.login()
        self.plus(learner)
        for item_id in (1, 2, 3):
            for module_number in (1, 2, 3):
                with self.subTest(item_id=item_id, module_number=module_number):
                    module_id = f"module-{module_number}"
                    first = self.start(learner, item_id, module_id)
                    failed = self.submit(learner, first, correct_count=6)
                    self.assertEqual(failed["result"]["score"], 75)
                    self.assertFalse(failed["result"]["passed"])
                    self.assertFalse(failed["result"]["course_completed"])
                    second = self.start(learner, item_id, module_id)
                    self.assertNotEqual(second["id"], first["id"])
                    self.assertTrue({q["id"] for q in first["questions"]}.isdisjoint(q["id"] for q in second["questions"]))
                    passed = self.submit(learner, second, correct_count=7)
                    self.assertGreaterEqual(passed["result"]["score"], 80)
                    self.assertTrue(passed["result"]["passed"])
                    overview = self.request(learner, f"/api/assessments/{item_id}")
                    module = overview["assessments"][module_number - 1]
                    self.assertTrue(module["passed"])
                    self.assertEqual(module["attempt_count"], 2)
                    self.assertEqual(len(module["history"]), 2)
                    self.assertEqual(module["best_score"], passed["result"]["score"])
                    self.assertEqual(overview["assessments"][-1]["locked"], module_number != 3)

    def test_concurrent_start_and_submit_do_not_duplicate_attempts(self):
        clients = [self.login(), self.login()]
        with ThreadPoolExecutor(max_workers=2) as pool:
            attempts = list(pool.map(self.start, clients))
        self.assertEqual(attempts[0]["id"], attempts[1]["id"])
        self.assertEqual(attempts[0]["questions"], attempts[1]["questions"])
        self.assertEqual(self.count_attempts(), 1)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda client: self.submit(client, attempts[0]), clients))
        self.assertEqual(results[0]["result"], results[1]["result"])
        self.assertEqual(self.count_attempts(), 1)
        history = self.request(clients[0], "/api/assessments/1")["assessments"][0]["history"]
        self.assertEqual(len(history), 1)

    def test_submission_is_idempotent_and_results_are_read_only(self):
        learner = self.login()
        attempt = self.start(learner)
        submitted = self.submit(learner, attempt)
        path = f"/api/assessment-attempts/{attempt['id']}"
        repeated = self.request(learner, path + "/submit", "POST", {"answers": {}})["attempt"]
        self.assertEqual(submitted["result"], repeated["result"])
        self.assertEqual(submitted["submitted_at"], repeated["submitted_at"])
        self.assertEqual(repeated["status"], "submitted")
        self.assertEqual(self.count_attempts(), 1)
        self.request(learner, path + "/save", "POST", {"answers": {}}, expected=409)
        restored = self.request(learner, path)["attempt"]
        self.assertEqual(restored["answers"], submitted["answers"])
        self.assertEqual(len(restored["result"]["feedback"]), 8)
        self.assertTrue(all(entry["explanation"] and entry["correct"] for entry in restored["result"]["feedback"]))

    def test_final_gate_completion_and_best_grade_for_all_courses(self):
        learner = self.login()
        self.plus(learner)
        for item_id in (1, 2, 3):
            with self.subTest(item_id=item_id):
                endpoint = f"/api/assessments/{item_id}"
                self.request(learner, endpoint + "/start", "POST", {"assessment_id": "final"}, expected=403)
                for module_id in ("module-1", "module-2"):
                    self.submit(learner, self.start(learner, item_id, module_id))
                self.request(learner, endpoint + "/start", "POST", {"assessment_id": "final"}, expected=403)
                self.submit(learner, self.start(learner, item_id, "module-3"))
                unlocked = self.request(learner, endpoint)
                self.assertFalse(unlocked["assessments"][-1]["locked"])
                self.assertFalse(unlocked["course"]["completed"])
                final = self.start(learner, item_id, "final")
                self.assertEqual(len(final["questions"]), 12)
                self.assertEqual(len({q["id"] for q in final["questions"]}), 12)
                from assessment_content import COURSE_ASSESSMENTS
                for module in COURSE_ASSESSMENTS[item_id]["modules"]:
                    module_questions = {q["id"] for q in module["questions"]}
                    self.assertEqual(sum(q["id"] in module_questions for q in final["questions"]), 4)
                completed = self.submit(learner, final)
                self.assertEqual(completed["result"]["score"], 100)
                self.assertTrue(completed["result"]["course_completed"])
                failed_retry = self.start(learner, item_id, "final")
                self.assertTrue({q["id"] for q in final["questions"]}.isdisjoint(q["id"] for q in failed_retry["questions"]))
                self.assertFalse(self.submit(learner, failed_retry, correct_count=0)["result"]["passed"])
                overview = self.request(learner, endpoint)
                self.assertTrue(overview["course"]["completed"])
                self.assertEqual(overview["course"]["passed_count"], 4)
                self.assertEqual(overview["assessments"][-1]["best_score"], 100)

    def test_roles_subscription_and_hidden_content_are_enforced(self):
        anonymous = self.client()
        self.request(anonymous, "/api/assessments/1", expected=401)
        self.request(anonymous, "/api/assessments/1/start", "POST", {"assessment_id": "module-1"}, expected=401)
        for role in ("educator", "admin"):
            client = self.login(role)
            self.request(client, "/api/assessments/1", expected=403)
            self.request(client, "/api/assessments/1/start", "POST", {"assessment_id": "module-1"}, expected=403)
        learner = self.login()
        self.request(learner, "/api/assessments/3", expected=403)
        self.request(learner, "/api/assessments/3/start", "POST", {"assessment_id": "module-1"}, expected=403)
        self.plus(learner)
        attempt = self.start(learner, 3)
        with server.connect_db() as connection:
            connection.execute("UPDATE subscriptions SET end_date = '2000-01-01' WHERE status = 'active'")
        for path, method, payload in (
            ("/api/assessments/3", "GET", None),
            (f"/api/assessment-attempts/{attempt['id']}", "GET", None),
            (f"/api/assessment-attempts/{attempt['id']}/save", "POST", {"answers": {}}),
            (f"/api/assessment-attempts/{attempt['id']}/submit", "POST", {"answers": self.answers(attempt)}),
        ):
            self.request(learner, path, method, payload, expected=403)
        self.plus(learner)
        with server.connect_db() as connection:
            connection.execute("UPDATE learning_items SET language = 'id' WHERE id = 3")
        self.request(learner, "/api/assessments/3", expected=403)
        self.request(learner, f"/api/assessment-attempts/{attempt['id']}", expected=403)

    def test_attempts_cannot_be_read_or_changed_by_another_learner(self):
        learner = self.login()
        attempt = self.start(learner)
        salt, digest = server.make_password("Second123!")
        with server.connect_db() as connection:
            connection.execute(
                "INSERT INTO users (full_name,email,password_salt,password_hash,role,created_at) VALUES (?,?,?,?,?,?)",
                ("Second Learner", "second@edustream.local", salt, digest, "learner", server.iso_now()),
            )
        other = self.login(email="second@edustream.local", password="Second123!")
        self.plus(other)
        path = f"/api/assessment-attempts/{attempt['id']}"
        self.request(other, path, expected=404)
        self.request(other, path + "/save", "POST", {"answers": {}}, expected=404)
        self.request(other, path + "/submit", "POST", {"answers": self.answers(attempt)}, expected=404)
        own = self.start(other)
        self.assertNotEqual(own["id"], attempt["id"])
        self.assertEqual(self.request(learner, path)["attempt"]["answers"], {})
        self.assertEqual(self.request(other, "/api/assessments/1")["assessments"][0]["attempt_count"], 0)

    def test_legacy_practice_scores_do_not_unlock_final(self):
        learner = self.login()
        answers = {q["id"]: q["correct_option_id"] for q in server.QUIZZES[1]["questions"]}
        self.request(learner, "/api/quiz/1/submit", "POST", {"answers": answers})
        self.request(learner, "/api/progress", "POST", {"item_id": 1, "progress": 100})
        overview = self.request(learner, "/api/assessments/1")
        self.assertEqual(overview["course"]["passed_count"], 0)
        self.assertTrue(overview["assessments"][-1]["locked"])
        self.assertEqual(self.request(learner, "/api/dashboard")["stats"]["completed"], 0)
        self.request(learner, "/api/assessments/1/start", "POST", {"assessment_id": "final"}, expected=403)

    def test_reinitialization_preserves_drafts_scores_and_legacy_data(self):
        learner = self.login()
        submitted = self.submit(learner, self.start(learner))
        draft = self.start(learner, assessment_id="module-2")
        partial = dict(list(self.answers(draft).items())[:2])
        self.request(learner, f"/api/assessment-attempts/{draft['id']}/save", "POST", {"answers": partial})
        with server.connect_db() as connection:
            before = {
                table: [tuple(row) for row in connection.execute(f"SELECT * FROM {table}")]
                for table in ("assessment_attempts", "quiz_attempts", "progress", "users")
            }
        server.initialize_database()
        server.initialize_database()
        with server.connect_db() as connection:
            for table, rows in before.items():
                self.assertEqual([tuple(row) for row in connection.execute(f"SELECT * FROM {table}")], rows)
        self.assertEqual(self.start(learner, assessment_id="module-2")["answers"], partial)
        restored = self.request(learner, f"/api/assessment-attempts/{submitted['id']}")["attempt"]
        self.assertEqual(restored["result"]["score"], 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
