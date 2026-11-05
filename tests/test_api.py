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


if __name__ == "__main__":
    unittest.main(verbosity=2)
