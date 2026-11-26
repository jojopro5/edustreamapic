"""Shared live-server test base for the newer test files."""

import http.cookiejar
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import server

ACCOUNTS = {
    "learner": ("learner@edustream.local", "Learn123!"),
    "educator": ("educator@edustream.local", "Teach123!"),
    "admin": ("admin@edustream.local", "Admin123!"),
}


class LiveServerTestCase(unittest.TestCase):
    db_name = "edustream-test.db"

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        server.DB_PATH = Path(cls.temp_dir.name) / cls.db_name
        cls.reset_auth_state()
        server.initialize_database(reset=True)
        cls.httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.EduStreamHandler)
        cls.host = f"127.0.0.1:{cls.httpd.server_port}"
        cls.base_url = f"http://{cls.host}"
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

    def client(self):
        return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def raw(self, client, path, method="GET", data=None, headers=None, expected=200):
        request = urllib.request.Request(self.base_url + path, data=data, method=method, headers=headers or {})
        try:
            response = client.open(request, timeout=10)
            status, body, response_headers = response.status, response.read(), response.headers
        except urllib.error.HTTPError as error:
            status, body, response_headers = error.code, error.read(), error.headers
        self.assertEqual(status, expected, body[:400])
        return body, response_headers

    def request(self, client, path, method="GET", payload=None, expected=200, headers=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        all_headers = {"Content-Type": "application/json", **(headers or {})}
        body, response_headers = self.raw(client, path, method, data, all_headers, expected)
        parsed = json.loads(body.decode("utf-8"))
        self.last_headers = response_headers
        return parsed

    def login(self, role=None, email=None, password=None):
        if role:
            email, password = ACCOUNTS[role]
        client = self.client()
        self.request(client, "/api/login", "POST", {"email": email, "password": password})
        return client

    def audit(self, event_type=None):
        with server.connect_db() as connection:
            sql = "SELECT * FROM audit_events" + (" WHERE event_type = ?" if event_type else "") + " ORDER BY id"
            return [dict(row) for row in connection.execute(sql, (event_type,) if event_type else ())]
