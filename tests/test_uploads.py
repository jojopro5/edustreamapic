"""T2 educator file upload tests (Student 2). IDs follow T2-UP-nn for the test register."""

import http.cookiejar
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import server
import uploads

PDF = b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + b"\x00" * 17
TXT = "Week 1 reading notes: passwords, phishing and MFA.\n".encode("utf-8")
HTML = b"<!DOCTYPE html><html><script>alert(1)</script></html>"


class UploadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        server.DB_PATH = Path(cls.temp_dir.name) / "edustream-uploads.db"
        cls.upload_root = server.DB_PATH.parent / "uploads"
        cls.reset_auth_state()
        server.initialize_database(reset=True)
        with server.connect_db() as connection:
            salt, digest = server.make_password("Teach456!")
            connection.execute(
                "INSERT INTO users (full_name, email, password_salt, password_hash, role, created_at) VALUES (?, ?, ?, ?, 'educator', ?)",
                ("Second Educator", "educator2@edustream.local", salt, digest, server.iso_now()),
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
        if hasattr(server, "SESSIONS"):
            server.SESSIONS.clear()
        if hasattr(server, "LOGIN_THROTTLE"):
            server.LOGIN_THROTTLE.reset()

    def setUp(self):
        self.reset_auth_state()

    def call(self, client, path, method="GET", data=None, headers=None, expected=200):
        request = urllib.request.Request(self.base_url + path, data=data, method=method, headers=headers or {})
        try:
            response = client.open(request, timeout=10)
            status, raw, response_headers = response.status, response.read(), response.headers
        except urllib.error.HTTPError as error:
            status, raw, response_headers = error.code, error.read(), error.headers
        self.assertEqual(status, expected, raw[:300])
        return raw, response_headers

    def json_call(self, client, path, method="GET", payload=None, expected=200):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        raw, _ = self.call(client, path, method, data, {"Content-Type": "application/json"}, expected)
        return json.loads(raw.decode("utf-8"))

    def login(self, email, password):
        client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.json_call(client, "/api/login", "POST", {"email": email, "password": password})
        return client

    def educator(self):
        return self.login("educator@edustream.local", "Teach123!")

    def admin(self):
        return self.login("admin@edustream.local", "Admin123!")

    def learner(self):
        return self.login("learner@edustream.local", "Learn123!")

    def new_item(self, client, title="Safe Data Handling Notes"):
        body = self.json_call(client, "/api/content", "POST", {
            "title": title, "category": "Cybersecurity", "content_type": "article", "language": "en",
            "duration_minutes": 20, "description": "Synthetic reading notes used to test educator uploads.",
        })
        return body["item_id"]

    def upload(self, client, item_id, name, data, expected=200):
        headers = {"Content-Type": "application/octet-stream", "X-File-Name": urllib.parse.quote(name)}
        raw, _ = self.call(client, f"/api/content/{item_id}/attachment", "POST", data, headers, expected)
        return json.loads(raw.decode("utf-8"))

    def stored_files(self):
        return sorted(path.name for path in self.upload_root.glob("*")) if self.upload_root.exists() else []

    def audit(self, event_type):
        with server.connect_db() as connection:
            return [row[0] for row in connection.execute("SELECT details FROM audit_events WHERE event_type = ?", (event_type,))]

    def set_status(self, item_id, status):
        with server.connect_db() as connection:
            connection.execute("UPDATE learning_items SET status = ? WHERE id = ?", (status, item_id))
            connection.commit()

    # Permitted use

    def test_T2_UP_01_educator_attaches_valid_files_and_admin_reviews_them(self):
        educator, admin = self.educator(), self.admin()
        for name, data in (("notes.pdf", PDF), ("diagram.png", PNG), ("reading.txt", TXT)):
            item_id = self.new_item(educator, f"Upload test {name}")
            info = self.upload(educator, item_id, name, data)["attachment"]
            self.assertEqual(info["name"], name)
            body, headers = self.call(admin, f"/api/content/{item_id}/attachment")
            self.assertEqual(body, data)
            self.assertTrue(headers["Content-Disposition"].startswith("attachment;"))
            self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
            self.assertIn("sandbox", headers["Content-Security-Policy"])
        pending = self.json_call(admin, "/api/dashboard")["pending_items"]
        self.assertTrue(any(item["attachment"] and item["attachment"]["name"] == "notes.pdf" for item in pending))
        # The uploaded names are never used on disk.
        self.assertFalse(any(name in self.stored_files() for name in ("notes.pdf", "diagram.png", "reading.txt")))
        self.assertTrue(self.audit("content_file_uploaded"))

    def test_T2_UP_02_entitled_learner_downloads_approved_file_only(self):
        educator, learner = self.educator(), self.learner()
        self.set_status(1, "pending")  # attach to an existing course while it is under review
        self.upload(educator, 1, "safety-checklist.pdf", PDF)
        self.set_status(1, "approved")
        body, _ = self.call(learner, "/api/content/1/attachment")
        self.assertEqual(body, PDF)
        access = self.json_call(learner, "/api/access/1")
        self.assertEqual(access["item"]["attachment"]["name"], "safety-checklist.pdf")
        self.call(learner, "/api/content/3/attachment", expected=403)  # not in the Starter plan

    # Prohibited use and failure cases

    def test_T2_UP_03_disallowed_types_and_disguised_files_are_rejected(self):
        educator = self.educator()
        item_id = self.new_item(educator)
        before = self.stored_files()
        cases = [
            ("setup.exe", b"MZ\x90\x00binary", 415),
            ("page.html", HTML, 415),
            ("report.pdf", HTML, 415),          # HTML renamed to .pdf
            ("photo.pdf", PNG, 415),            # PNG renamed to .pdf
            ("notes.txt", HTML, 415),           # markup is not plain text
            ("notes.txt", b"\xff\xfe\x00bad", 415),
            ("noextension", PDF, 400),
            ("empty.pdf", b"", 400),
        ]
        for name, data, status in cases:
            with self.subTest(name=name):
                self.upload(educator, item_id, name, data, status)
        self.assertEqual(self.stored_files(), before)
        reasons = self.audit("content_file_rejected")
        self.assertTrue(any("signature_mismatch" in reason for reason in reasons))
        self.assertTrue(any("extension" in reason for reason in reasons))

    def test_T2_UP_04_oversized_file_is_refused(self):
        educator = self.educator()
        item_id = self.new_item(educator)
        too_big = PDF + b"0" * (uploads.MAX_BYTES - len(PDF) + 1)
        try:
            self.upload(educator, item_id, "big.pdf", too_big, 413)
        except (ConnectionError, urllib.error.URLError):
            pass  # the server may close the connection before reading the body
        self.assertTrue(any("too_large" in reason for reason in self.audit("content_file_rejected")))

    def test_T2_UP_05_path_traversal_name_cannot_choose_storage_path(self):
        educator = self.educator()
        item_id = self.new_item(educator)
        info = self.upload(educator, item_id, "../../server.py/..\\evil<script>.pdf", PDF)["attachment"]
        self.assertEqual(info["name"], "evil_script_.pdf")
        self.assertFalse((server.ROOT / "evil.pdf").exists())
        with server.connect_db() as connection:
            stored = connection.execute("SELECT stored_name FROM content_files WHERE learning_item_id = ?", (item_id,)).fetchone()[0]
        self.assertRegex(stored, r"^[0-9a-f]{32}\.pdf$")
        self.assertTrue((self.upload_root / stored).is_file())

    def test_T2_UP_06_wrong_owner_wrong_role_and_reviewed_items_are_refused(self):
        educator, admin, learner = self.educator(), self.admin(), self.learner()
        other = self.login("educator2@edustream.local", "Teach456!")
        item_id = self.new_item(educator)
        self.upload(other, item_id, "hijack.pdf", PDF, 403)
        self.call(other, f"/api/content/{item_id}/attachment", expected=403)
        headers = {"Content-Type": "application/octet-stream", "X-File-Name": "x.pdf"}
        self.call(learner, f"/api/content/{item_id}/attachment", "POST", PDF, headers, 403)
        self.upload(educator, item_id, "notes.pdf", PDF)
        self.call(learner, f"/api/content/{item_id}/attachment", expected=403)  # pending: never visible to learners
        self.json_call(admin, f"/api/admin/content/{item_id}/review", "POST", {"decision": "approved"})
        self.upload(educator, item_id, "swapped-after-approval.pdf", PDF, 409)
        anonymous = urllib.request.build_opener()
        self.call(anonymous, f"/api/content/{item_id}/attachment", expected=401)
        self.assertTrue(any("not_owner" in reason for reason in self.audit("content_file_rejected")))
        self.assertTrue(any("not_pending" in reason for reason in self.audit("content_file_rejected")))
        self.assertTrue(self.audit("content_file_denied"))

    def test_T2_UP_07_replacing_a_pending_file_removes_the_old_one(self):
        educator = self.educator()
        item_id = self.new_item(educator)
        self.upload(educator, item_id, "draft.pdf", PDF)
        with server.connect_db() as connection:
            first = connection.execute("SELECT stored_name FROM content_files WHERE learning_item_id = ?", (item_id,)).fetchone()[0]
        info = self.upload(educator, item_id, "final.txt", TXT)["attachment"]
        self.assertTrue(info["replaced"])
        self.assertFalse((self.upload_root / first).exists())
        self.assertTrue(any("(replaced)" in detail for detail in self.audit("content_file_uploaded")))

    def test_T2_UP_08_tampered_file_fails_integrity_check(self):
        educator, admin = self.educator(), self.admin()
        item_id = self.new_item(educator)
        self.upload(educator, item_id, "notes.pdf", PDF)
        with server.connect_db() as connection:
            stored = connection.execute("SELECT stored_name FROM content_files WHERE learning_item_id = ?", (item_id,)).fetchone()[0]
        (self.upload_root / stored).write_bytes(PDF + b"tampered")
        self.call(admin, f"/api/content/{item_id}/attachment", expected=500)
        self.assertTrue(self.audit("content_file_integrity_failed"))


if __name__ == "__main__":
    unittest.main()
