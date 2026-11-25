"""T3 learner feedback tests (Student 3). IDs follow T3-FB-nn for the test register."""

import http.cookiejar
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import feedback
import server


class FeedbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        server.DB_PATH = Path(cls.temp_dir.name) / "edustream-feedback.db"
        cls.reset_auth_state()
        server.initialize_database(reset=True)
        with server.connect_db() as connection:
            salt, digest = server.make_password("Learn456!")
            cursor = connection.execute(
                "INSERT INTO users (full_name, email, password_salt, password_hash, role, created_at) VALUES (?, ?, ?, ?, 'learner', ?)",
                ("Bilal Osei", "learner2@edustream.local", salt, digest, server.iso_now()),
            )
            starter = connection.execute("SELECT id FROM plans WHERE code = 'starter'").fetchone()[0]
            connection.execute(
                "INSERT INTO subscriptions (user_id, plan_id, status, start_date, end_date, created_at) VALUES (?, ?, 'active', date('now'), date('now', '+30 day'), ?)",
                (cursor.lastrowid, starter, server.iso_now()),
            )
            connection.commit()
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

    @staticmethod
    def reset_auth_state():
        # Works with the in-memory sessions on main and the login throttle from the login-hardening PR.
        if hasattr(server, "SESSIONS"):
            server.SESSIONS.clear()
        if hasattr(server, "LOGIN_THROTTLE"):
            server.LOGIN_THROTTLE.reset()

    def setUp(self):
        self.reset_auth_state()
        with server.connect_db() as connection:
            connection.execute("DELETE FROM feedback")
            connection.commit()

    def request(self, client, path, method="GET", payload=None, expected=200):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(self.base_url + path, data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            response = client.open(request, timeout=5)
            status, body = response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            status, body = error.code, json.loads(error.read().decode("utf-8"))
        self.assertEqual(status, expected, body)
        return body

    def login(self, email, password):
        client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.request(client, "/api/login", "POST", {"email": email, "password": password})
        return client

    def learner(self):
        return self.login("learner@edustream.local", "Learn123!")

    def learner2(self):
        return self.login("learner2@edustream.local", "Learn456!")

    def post(self, client, item_id, text, expected=200):
        return self.request(client, f"/api/feedback/{item_id}", "POST", {"body": text}, expected)

    def audit_details(self, event_type):
        with server.connect_db() as connection:
            return [row[0] for row in connection.execute("SELECT details FROM audit_events WHERE event_type = ?", (event_type,))]

    # Permitted use

    def test_T3_FB_01_entitled_learner_posts_and_others_see_it(self):
        amina, bilal = self.learner(), self.learner2()
        posted = self.post(amina, 1, "  The phishing examples were really clear.  ")["feedback"]
        self.assertEqual(posted["body"], "The phishing examples were really clear.")
        listed = self.request(bilal, "/api/feedback/1")["feedback"]
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["author"], "Amina C.")
        self.assertFalse(listed[0]["mine"])
        self.assertNotIn("email", listed[0])
        self.assertNotIn("user_id", listed[0])

    def test_T3_FB_02_author_edits_and_deletes_own_feedback(self):
        amina = self.learner()
        entry = self.post(amina, 1, "First draft of my comment")["feedback"]
        edited = self.request(amina, f"/api/feedback-entries/{entry['id']}/edit", "POST", {"body": "Edited comment"})["feedback"]
        self.assertEqual(edited["body"], "Edited comment")
        self.assertIsNotNone(edited["edited_at"])
        self.request(amina, f"/api/feedback-entries/{entry['id']}/delete", "POST", {})
        self.assertEqual(self.request(amina, "/api/feedback/1")["feedback"], [])

    # Prohibited use and failure cases

    def test_T3_FB_03_script_payload_is_stored_as_inert_text(self):
        amina = self.learner()
        payloads = ['<script>alert("x")</script>', '<img src=x onerror="alert(1)">', '"><svg onload=alert(1)>']
        for payload in payloads:
            self.post(amina, 1, payload)
        listed = self.request(amina, "/api/feedback/1")["feedback"]
        # The API returns exactly what was typed, as JSON text; the UI writes it with textContent.
        self.assertEqual(sorted(entry["body"] for entry in listed), sorted(payloads))
        script = (server.STATIC_ROOT / "feedback.js").read_text(encoding="utf-8")
        for sink in (".innerHTML", ".outerHTML", "insertAdjacentHTML", "document.write"):
            self.assertNotIn(sink, script)

    def test_T3_FB_04_learner_cannot_edit_or_delete_another_learners_feedback(self):
        amina, bilal = self.learner(), self.learner2()
        entry = self.post(amina, 1, "Amina's original comment")["feedback"]
        self.request(bilal, f"/api/feedback-entries/{entry['id']}/edit", "POST", {"body": "Defaced by Bilal"}, 404)
        self.request(bilal, f"/api/feedback-entries/{entry['id']}/delete", "POST", {}, 404)
        listed = self.request(amina, "/api/feedback/1")["feedback"]
        self.assertEqual([item["body"] for item in listed], ["Amina's original comment"])

    def test_T3_FB_05_unentitled_course_and_wrong_roles_are_denied(self):
        amina = self.learner()  # Starter plan: course 3 is not included
        self.request(amina, "/api/feedback/3", expected=403)
        self.post(amina, 3, "Trying to post without access", 403)
        self.post(amina, 4, "Pending item is never visible", 403)
        self.assertTrue(self.audit_details("feedback_access_denied"))
        educator = self.login("educator@edustream.local", "Teach123!")
        admin = self.login("admin@edustream.local", "Admin123!")
        self.post(educator, 1, "Educators do not post learner feedback", 403)
        self.post(admin, 1, "Admins moderate instead", 403)
        anonymous = urllib.request.build_opener()
        self.request(anonymous, "/api/feedback/1", expected=401)

    def test_T3_FB_06_invalid_bodies_are_rejected_without_saving(self):
        amina = self.learner()
        for bad in ["", " ", "x", "a" * 501, None, 42, ["list"], "\u0000​‮"]:
            self.request(amina, "/api/feedback/1", "POST", {"body": bad}, 400)
        self.assertEqual(self.request(amina, "/api/feedback/1")["feedback"], [])
        cleaned = self.post(amina, 1, "ok\u0000 text‮ with\n\n\n\nspacing")["feedback"]
        self.assertEqual(cleaned["body"], "ok text with\n\nspacing")

    def test_T3_FB_07_rate_limit_blocks_flooding(self):
        amina, bilal = self.learner(), self.learner2()
        for number in range(feedback.RATE_LIMIT_COUNT):
            self.post(amina, 1, f"Comment number {number}")
        self.post(amina, 1, "One too many", 429)
        self.assertTrue(self.audit_details("feedback_rate_limited"))
        self.post(bilal, 1, "Another learner is unaffected")

    def test_T3_FB_08_admin_hides_and_restores_and_hidden_cannot_be_edited(self):
        amina = self.learner()
        admin = self.login("admin@edustream.local", "Admin123!")
        entry = self.post(amina, 1, "Spam spam spam")["feedback"]
        self.request(admin, f"/api/admin/feedback/{entry['id']}/moderate", "POST", {"action": "hide"})
        self.assertEqual(self.request(amina, "/api/feedback/1")["feedback"], [])
        self.request(amina, f"/api/feedback-entries/{entry['id']}/edit", "POST", {"body": "Sneaky edit"}, 404)
        self.request(amina, f"/api/feedback-entries/{entry['id']}/delete", "POST", {}, 404)
        dashboard = self.request(admin, "/api/dashboard")
        record = next(item for item in dashboard["feedback"] if item["id"] == entry["id"])
        self.assertEqual(record["status"], "hidden")
        self.assertEqual(record["moderator"], "System Administrator")
        self.request(admin, f"/api/admin/feedback/{entry['id']}/moderate", "POST", {"action": "restore"})
        self.assertEqual(len(self.request(amina, "/api/feedback/1")["feedback"]), 1)
        self.request(amina, f"/api/admin/feedback/{entry['id']}/moderate", "POST", {"action": "hide"}, 403)
        self.request(admin, f"/api/admin/feedback/{entry['id']}/moderate", "POST", {"action": "delete"}, 400)

    def test_T3_FB_09_audit_events_never_contain_comment_text(self):
        amina = self.learner()
        secret = "unique-comment-text-7731"
        entry = self.post(amina, 1, secret)["feedback"]
        self.request(amina, f"/api/feedback-entries/{entry['id']}/edit", "POST", {"body": secret + " edited"})
        details = self.audit_details("feedback_posted") + self.audit_details("feedback_edited")
        self.assertTrue(details)
        self.assertFalse(any(secret in detail for detail in details))


if __name__ == "__main__":
    unittest.main()
