"""Admin review guard rails, educator resubmission, cross-site request checks and static/HEAD handling.

Test IDs:
  REV_01-04  review applies to pending items only, rejection needs a reason, educators see it and can resubmit
  CSRF_01-03 state-changing requests from another site or without a JSON body are refused
  WEB_01-04  missing assets 404, HEAD works, demo logins can be turned off, unknown ids are not audited
"""

import http.client
import http.cookiejar
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import server


class QuietHandler(server.EduStreamHandler):
    def log_message(self, fmt, *args):
        pass


NEW_ITEM = {
    "title": "Responsible Data Sharing",
    "category": "Privacy",
    "description": "A practical module about sharing learning data safely and with clear permission.",
    "content_type": "course",
    "duration_minutes": 40,
}


class ReviewAndRequestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_db_path = server.DB_PATH
        cls.temp_dir = tempfile.TemporaryDirectory()
        server.DB_PATH = Path(cls.temp_dir.name) / "review-test.db"
        cls.httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        cls.port = cls.httpd.server_port
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=3)
        server.DB_PATH = cls.original_db_path
        cls.temp_dir.cleanup()

    def setUp(self):
        if hasattr(server, "LOGIN_THROTTLE"):
            server.LOGIN_THROTTLE.reset()
        server.initialize_database(reset=True)
        self.httpd.demo_logins = True

    def client(self):
        return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(self, client, path, method="GET", payload=None, expected=200, headers=None):
        request = urllib.request.Request(
            self.base_url + path,
            data=None if payload is None else json.dumps(payload).encode("utf-8"),
            method=method,
            headers={"Content-Type": "application/json", **(headers or {})},
        )
        try:
            response = client.open(request, timeout=5)
            status, body = response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            status, body = error.code, json.loads(error.read().decode("utf-8"))
        self.assertEqual(status, expected, body)
        return body

    def login(self, role):
        account = next(entry for entry in server.DEMO_ACCOUNTS if entry["role"] == role)
        client = self.client()
        self.request(client, "/api/login", "POST", {"email": account["email"], "password": account["password"]})
        return client

    def submit_item(self, educator):
        return self.request(educator, "/api/content", "POST", NEW_ITEM)["item_id"]

    def item_row(self, item_id):
        with server.connect_db() as connection:
            return dict(connection.execute("SELECT * FROM learning_items WHERE id = ?", (item_id,)).fetchone())

    # REV_01
    def test_only_pending_items_can_be_reviewed(self):
        admin = self.login("admin")
        body = self.request(admin, "/api/admin/content/1/review", "POST",
                            {"decision": "rejected", "reason": "Pulling a live course"}, expected=409)
        self.assertIn("already approved", body["error"])
        self.assertEqual(self.item_row(1)["status"], "approved")
        learner = self.login("learner")
        titles = [item["title"] for item in self.request(learner, "/api/dashboard")["items"]]
        self.assertIn("Digital Safety Foundations", titles)

    # REV_02
    def test_rejection_requires_a_reason_and_records_it(self):
        educator, admin = self.login("educator"), self.login("admin")
        item_id = self.submit_item(educator)
        for payload in ({"decision": "rejected"}, {"decision": "rejected", "reason": "too short"}):
            self.request(admin, f"/api/admin/content/{item_id}/review", "POST", payload, expected=400)
        self.assertEqual(self.item_row(item_id)["status"], "pending")
        reason = "Add a clear learning outcome to the description."
        self.request(admin, f"/api/admin/content/{item_id}/review", "POST", {"decision": "rejected", "reason": reason})
        row = self.item_row(item_id)
        self.assertEqual((row["status"], row["review_note"]), ("rejected", reason))
        self.assertTrue(row["reviewed_at"])
        self.request(admin, f"/api/admin/content/{item_id}/review", "POST", {"decision": "approved"}, expected=409)
        mine = next(item for item in self.request(educator, "/api/dashboard")["items"] if item["id"] == item_id)
        self.assertEqual(mine["review_note"], reason)

    # REV_03
    def test_educator_can_edit_and_resubmit_only_their_rejected_item(self):
        educator, admin = self.login("educator"), self.login("admin")
        item_id = self.submit_item(educator)
        changed = {**NEW_ITEM, "title": "Responsible Data Sharing (revised)"}
        self.request(educator, f"/api/content/{item_id}/resubmit", "POST", changed, expected=409)
        self.request(admin, f"/api/admin/content/{item_id}/review", "POST",
                     {"decision": "rejected", "reason": "Please add a clear learning outcome."})
        self.request(admin, f"/api/content/{item_id}/resubmit", "POST", changed, expected=403)
        self.request(educator, "/api/content/999/resubmit", "POST", changed, expected=404)
        self.request(educator, f"/api/content/{item_id}/resubmit", "POST", {**changed, "title": "No"}, expected=400)
        self.request(educator, f"/api/content/{item_id}/resubmit", "POST", changed)
        row = self.item_row(item_id)
        self.assertEqual((row["status"], row["title"]), ("pending", changed["title"]))
        pending = self.request(admin, "/api/dashboard")["pending_items"]
        self.assertIn(item_id, [item["id"] for item in pending])
        self.request(admin, f"/api/admin/content/{item_id}/review", "POST", {"decision": "approved"})
        self.assertIsNone(self.item_row(item_id)["review_note"])

    # REV_04
    def test_review_columns_are_added_to_an_older_database(self):
        with server.connect_db() as connection:
            connection.execute("ALTER TABLE learning_items DROP COLUMN review_note")
            connection.execute("ALTER TABLE learning_items DROP COLUMN reviewed_at")
            connection.commit()
        server.initialize_database()
        with server.connect_db() as connection:
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(learning_items)")}
            count = connection.execute("SELECT COUNT(*) FROM learning_items").fetchone()[0]
        self.assertTrue({"review_note", "reviewed_at"} <= columns)
        self.assertEqual(count, 4)

    # CSRF_01
    def test_requests_from_another_origin_are_refused(self):
        learner = self.login("learner")
        for headers in ({"Origin": "https://evil.example"}, {"Origin": "null"}, {"Sec-Fetch-Site": "cross-site"},
                        {"Sec-Fetch-Site": "same-site"}):
            with self.subTest(headers=headers):
                body = self.request(learner, "/api/progress", "POST", {"item_id": 1, "progress": 90},
                                    expected=403, headers=headers)
                self.assertIn("Cross-site", body["error"])
        self.request(learner, "/api/progress", "POST", {"item_id": 1, "progress": 90},
                     headers={"Origin": self.base_url, "Sec-Fetch-Site": "same-origin"})

    # CSRF_02
    def test_non_json_content_type_is_refused(self):
        learner = self.login("learner")
        for content_type in ("text/plain", "application/x-www-form-urlencoded", "multipart/form-data"):
            with self.subTest(content_type=content_type):
                body = self.request(learner, "/api/progress", "POST", {"item_id": 1, "progress": 90},
                                    expected=403, headers={"Content-Type": content_type})
                self.assertIn("application/json", body["error"])
        with server.connect_db() as connection:
            progress = connection.execute("SELECT progress_percent FROM progress WHERE learning_item_id = 1").fetchone()[0]
        self.assertEqual(progress, 65)

    # CSRF_03
    def test_attachment_upload_needs_its_custom_header(self):
        educator = self.login("educator")
        item_id = self.submit_item(educator)
        request = urllib.request.Request(self.base_url + f"/api/content/{item_id}/attachment", data=b"%PDF-1.4 test",
                                         method="POST", headers={"Content-Type": "application/octet-stream"})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            educator.open(request, timeout=5)
        self.assertEqual(caught.exception.code, 403)

    # WEB_01
    def test_missing_asset_is_404_but_app_paths_fall_back(self):
        client = self.client()
        with self.assertRaises(urllib.error.HTTPError) as caught:
            client.open(self.base_url + "/missing-script.js", timeout=5)
        self.assertEqual(caught.exception.code, 404)
        with client.open(self.base_url + "/learning", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertIn(b"<!doctype html>", response.read().lower())

    # WEB_02
    def test_head_returns_headers_without_a_body(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        connection.request("HEAD", "/styles.css")
        response = connection.getresponse()
        self.assertEqual(response.status, 200)
        self.assertGreater(int(response.getheader("Content-Length")), 0)
        self.assertEqual(response.read(), b"")
        connection.close()

    # WEB_03
    def test_demo_logins_can_be_turned_off(self):
        client = self.client()
        session = self.request(client, "/api/session")
        self.assertEqual({entry["role"] for entry in session["demo_accounts"]}, {"learner", "educator", "admin"})
        self.httpd.demo_logins = False
        self.assertEqual(self.request(client, "/api/session")["demo_accounts"], [])
        index = (server.STATIC_ROOT / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("Admin123!", index)

    # WEB_04
    def test_unknown_item_ids_are_not_written_to_the_audit_log(self):
        learner = self.login("learner")

        def denied_count():
            with server.connect_db() as connection:
                return connection.execute("SELECT COUNT(*) FROM audit_events WHERE event_type = 'access_denied'").fetchone()[0]

        for item_id in (900, 901, 902):
            self.request(learner, f"/api/access/{item_id}", expected=403)
        self.assertEqual(denied_count(), 0)
        self.request(learner, "/api/access/3", expected=403)
        self.assertEqual(denied_count(), 1)


if __name__ == "__main__":
    unittest.main()
