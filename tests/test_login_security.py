import http.cookiejar
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import server


class QuietHandler(server.EduStreamHandler):
    def log_message(self, fmt, *args):
        pass


class LoginSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_db_path = server.DB_PATH
        cls.temp_dir = tempfile.TemporaryDirectory()
        server.DB_PATH = Path(cls.temp_dir.name) / "login-security-test.db"
        server.initialize_database(reset=True)

    @classmethod
    def tearDownClass(cls):
        server.DB_PATH = cls.original_db_path
        cls.temp_dir.cleanup()

    def setUp(self):
        server.LOGIN_THROTTLE.reset()
        self.start_server()

    def tearDown(self):
        self.stop_server()
        server.LOGIN_THROTTLE.reset()

    def start_server(self, secure_cookies=False):
        self.httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        self.httpd.secure_cookies = secure_cookies
        self.base_url = f"http://127.0.0.1:{self.httpd.server_port}"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def stop_server(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=3)

    def client(self):
        jar = http.cookiejar.CookieJar()
        return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def call(self, client, path, method="GET", payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(self.base_url + path, data=data, method=method,
                                         headers={"Content-Type": "application/json"})
        try:
            response = client.open(request, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        return response.status, dict(response.headers), json.loads(response.read().decode("utf-8")), response.headers

    def login(self, client, password="Learn123!", email="learner@edustream.local"):
        return self.call(client, "/api/login", "POST", {"email": email, "password": password})

    def test_repeated_failures_are_rate_limited_with_retry_after(self):
        client = self.client()
        for _ in range(server.LOGIN_MAX_FAILURES_PER_ACCOUNT):
            status, _, _, _ = self.login(client, password="wrong")
            self.assertEqual(status, 401)
        status, headers, body, _ = self.login(client, password="wrong")
        self.assertEqual(status, 429)
        self.assertGreater(int(headers["Retry-After"]), 0)
        self.assertFalse(body["ok"])
        # Even the correct password is refused while the lockout is active.
        status, _, _, _ = self.login(client)
        self.assertEqual(status, 429)
        # Other accounts from the same client are not locked by one account's failures.
        status, _, _, _ = self.login(client, email="educator@edustream.local", password="Teach123!")
        self.assertEqual(status, 200)

    def test_lockout_expires_after_the_window(self):
        client = self.client()
        for _ in range(server.LOGIN_MAX_FAILURES_PER_ACCOUNT):
            self.login(client, password="wrong")
        self.assertEqual(self.login(client)[0], 429)
        real_monotonic = server.time.monotonic
        with patch.object(server.time, "monotonic", lambda: real_monotonic() + server.LOGIN_WINDOW_SECONDS + 1):
            self.assertEqual(self.login(client)[0], 200)

    def test_success_clears_account_failures(self):
        client = self.client()
        for _ in range(server.LOGIN_MAX_FAILURES_PER_ACCOUNT - 1):
            self.login(client, password="wrong")
        self.assertEqual(self.login(client)[0], 200)
        for _ in range(server.LOGIN_MAX_FAILURES_PER_ACCOUNT - 1):
            self.assertEqual(self.login(client, password="wrong")[0], 401)

    def test_per_client_cap_covers_many_emails(self):
        client = self.client()
        for index in range(server.LOGIN_MAX_FAILURES_PER_CLIENT):
            self.login(client, email=f"guess{index}@example.com", password="wrong")
        self.assertEqual(self.login(client, email="another@example.com", password="wrong")[0], 429)

    def test_sessions_are_stored_hashed_and_survive_restart(self):
        jar = http.cookiejar.CookieJar()
        client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        self.assertEqual(self.login(client)[0], 200)
        token = next(cookie.value for cookie in jar if cookie.name == server.SESSION_COOKIE)
        with server.connect_db() as connection:
            stored = [row["token_hash"] for row in connection.execute("SELECT token_hash FROM sessions")]
        self.assertNotIn(token, stored)
        self.assertIn(server.hash_token(token), stored)
        self.stop_server()
        self.start_server()
        status, _, body, _ = self.call(client, "/api/dashboard")
        self.assertEqual(status, 200, body)

    def test_logout_deletes_the_stored_session(self):
        client = self.client()
        self.login(client)
        with server.connect_db() as connection:
            before = connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        self.assertEqual(self.call(client, "/api/logout", "POST", {})[0], 200)
        with server.connect_db() as connection:
            after = connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        self.assertEqual(after, before - 1)
        self.assertEqual(self.call(client, "/api/dashboard")[0], 401)

    def test_expired_sessions_are_rejected_and_purged(self):
        client = self.client()
        self.login(client)
        with server.connect_db() as connection:
            connection.execute("UPDATE sessions SET expires_at = ?",
                               ((server.utc_now() - timedelta(seconds=1)).isoformat(timespec="microseconds"),))
        self.assertEqual(self.call(client, "/api/dashboard")[0], 401)
        with server.connect_db() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0], 0)

    def test_cookie_flags_follow_server_setting(self):
        _, _, _, headers = self.login(self.client())
        cookie = headers["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)
        self.assertNotIn("Secure", cookie)

        self.stop_server()
        self.start_server(secure_cookies=True)
        _, _, _, headers = self.login(self.client())
        self.assertIn("; Secure", headers["Set-Cookie"])
        _, _, _, headers = self.call(self.client(), "/api/logout", "POST", {})
        self.assertIn("; Secure", headers["Set-Cookie"])

    def test_loopback_detection(self):
        for host in ("127.0.0.1", "127.0.1.1", "localhost", "::1"):
            self.assertTrue(server.is_loopback_host(host), host)
        for host in ("0.0.0.0", "192.168.1.10", "edustream.example.com"):
            self.assertFalse(server.is_loopback_host(host), host)


if __name__ == "__main__":
    unittest.main(verbosity=2)
