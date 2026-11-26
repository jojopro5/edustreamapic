"""T4 backup and restore tests. IDs match docs/T4_backup_restore.md (T4_BR_01 to T4_BR_14).

All data is the synthetic demo dataset created by server.seed_database.
"""
import http.cookiejar
import json
import shutil
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import backups
import server


class BackupRestoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_db = server.DB_PATH
        cls.httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.EduStreamHandler)
        cls.base_url = f"http://127.0.0.1:{cls.httpd.server_port}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=3)
        server.DB_PATH = cls.original_db

    def setUp(self):
        # A fresh database and backup folder per test, so restores cannot leak between tests.
        self.temp_dir = tempfile.mkdtemp()
        server.DB_PATH = Path(self.temp_dir) / "edustream-test.db"
        if hasattr(server, "SESSIONS"):
            server.SESSIONS.clear()
        if hasattr(server, "LOGIN_THROTTLE"):
            server.LOGIN_THROTTLE.reset()
        server.initialize_database(reset=True)
        self.db = server.DB_PATH

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # --- helpers -------------------------------------------------------------

    def client(self):
        return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(self, client, path, method="GET", payload=None, expected=200):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.base_url + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        try:
            response = client.open(req, timeout=10)
            status, body = response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            status, body = error.code, json.loads(error.read().decode("utf-8"))
        self.assertEqual(status, expected, body)
        return body

    def login(self, role):
        credentials = {
            "learner": ("learner@edustream.local", "Learn123!"),
            "educator": ("educator@edustream.local", "Teach123!"),
            "admin": ("admin@edustream.local", "Admin123!"),
        }[role]
        client = self.client()
        self.request(client, "/api/login", "POST", {"email": credentials[0], "password": credentials[1]})
        return client

    def query(self, sql, params=()):
        connection = sqlite3.connect(self.db)
        try:
            return connection.execute(sql, params).fetchall()
        finally:
            connection.close()

    def audit_types(self):
        return [row[0] for row in self.query("SELECT event_type FROM audit_events ORDER BY id")]

    def learner_role(self):
        return self.query("SELECT role FROM users WHERE email = 'learner@edustream.local'")[0][0]

    # --- tests ---------------------------------------------------------------

    def test_T4_BR_01_admin_creates_signed_verified_backup(self):
        admin = self.login("admin")
        created = self.request(admin, "/api/admin/backups", "POST", {})
        name = created["backup"]
        listing = self.request(admin, "/api/admin/backups")["backups"]
        self.assertEqual([entry["name"] for entry in listing], [name])
        self.assertTrue(listing[0]["ok"], listing[0]["problems"])
        manifest = json.loads((backups.backup_dir(self.db) / (name[:-3] + ".json")).read_text())
        self.assertEqual(len(manifest["hmac"]), 64)
        self.assertEqual(manifest["row_counts"]["users"], 3)
        self.assertIn("backup_created", self.audit_types())
        # The signing key is kept outside the backup folder.
        self.assertFalse((backups.backup_dir(self.db) / "backup.key").exists())
        self.assertTrue(backups.key_path(self.db).exists())

    def test_T4_BR_02_only_admins_can_use_backups(self):
        name = backups.create_backup(self.db, "test")["file"]
        anonymous = self.client()
        self.request(anonymous, "/api/admin/backups", expected=401)
        self.request(anonymous, "/api/admin/backups", "POST", {}, expected=401)
        for role in ("learner", "educator"):
            client = self.login(role)
            self.request(client, "/api/admin/backups", expected=403)
            self.request(client, "/api/admin/backups", "POST", {}, expected=403)
            self.request(client, f"/api/admin/backups/{name}/verify", "POST", {}, expected=403)
            self.request(client, f"/api/admin/backups/{name}/restore", "POST", {"confirm": name}, expected=403)

    def test_T4_BR_03_path_traversal_and_unknown_names_are_rejected(self):
        admin = self.login("admin")
        for bad in ("..%2Fedustream-test.db", "edustream-test.db", "edustream-20260101T000000Z-zzzzzzzz.db"):
            self.request(admin, f"/api/admin/backups/{bad}/restore", "POST", {"confirm": bad}, expected=404)
        with self.assertRaises(backups.BackupError):
            backups.verify_backup(self.db, "../edustream-test.db")
        self.assertEqual(self.query("SELECT COUNT(*) FROM users")[0][0], 3)

    def test_T4_BR_04_seeded_tampered_backup_is_detected_and_refused(self):
        """Seeded fault: learner promoted to admin inside the backup, SHA-256 recomputed."""
        name = backups.seed_fault(self.db, "tamper")["file"]
        admin = self.login("admin")
        verdict = self.request(admin, f"/api/admin/backups/{name}/verify", "POST", {})
        self.assertFalse(verdict["valid"])
        self.assertTrue(any(p.startswith("T4_C02 manifest signature") for p in verdict["problems"]), verdict)
        # The SHA-256 was recomputed, so only the signature check catches it.
        self.assertFalse(any(p.startswith("T4_C03") for p in verdict["problems"]), verdict)
        refused = self.request(admin, f"/api/admin/backups/{name}/restore", "POST", {"confirm": name}, expected=409)
        self.assertIn("not restored", refused["error"])
        self.assertEqual(self.learner_role(), "learner")
        types = self.audit_types()
        self.assertIn("backup_verify_failed", types)
        self.assertIn("backup_restore_refused", types)
        details = self.query("SELECT details FROM audit_events WHERE event_type = 'backup_restore_refused'")[0][0]
        self.assertIn("outcome=refused", details)
        self.assertIn(name, details)
        # The admin session still works: nothing was restored.
        self.request(admin, "/api/admin/backups")

    def test_T4_BR_05_corrupted_backup_is_refused(self):
        name = backups.seed_fault(self.db, "corrupt")["file"]
        admin = self.login("admin")
        refused = self.request(admin, f"/api/admin/backups/{name}/restore", "POST", {"confirm": name}, expected=409)
        self.assertIn("T4_C03 SHA-256 digest differs from the manifest", refused["problems"])
        self.assertEqual(self.query("SELECT COUNT(*) FROM users")[0][0], 3)

    def test_T4_BR_06_forged_unsigned_manifest_is_refused(self):
        name = backups.seed_fault(self.db, "unsigned")["file"]
        result = backups.verify_backup(self.db, name)
        self.assertFalse(result["ok"])
        self.assertTrue(result["problems"][0].startswith("T4_C02 manifest signature"))
        with self.assertRaises(backups.BackupError):
            backups.restore_backup(self.db, name, "test")

    def test_T4_BR_07_missing_manifest_or_file_is_refused(self):
        first = backups.create_backup(self.db, "test")["file"]
        second = backups.create_backup(self.db, "test")["file"]
        (backups.backup_dir(self.db) / (first[:-3] + ".json")).unlink()
        (backups.backup_dir(self.db) / second).unlink()
        self.assertEqual(backups.verify_backup(self.db, first)["problems"], ["T4_C02 manifest is missing"])
        self.assertIn("T4_C03 backup file is missing", backups.verify_backup(self.db, second)["problems"])
        admin = self.login("admin")
        for name in (first, second):
            self.request(admin, f"/api/admin/backups/{name}/restore", "POST", {"confirm": name}, expected=409)

    def test_T4_BR_08_valid_restore_recovers_data_keeps_audit_and_ends_sessions(self):
        admin = self.login("admin")
        name = self.request(admin, "/api/admin/backups", "POST", {})["backup"]
        # A change after the backup: approve the pending workshop.
        pending_id = self.query("SELECT id FROM learning_items WHERE status = 'pending'")[0][0]
        self.request(admin, f"/api/admin/content/{pending_id}/review", "POST", {"decision": "approved"})
        learner = self.login("learner")

        restored = self.request(admin, f"/api/admin/backups/{name}/restore", "POST", {"confirm": name})
        self.assertIn("sign in again", restored["message"])
        self.assertEqual(self.query("SELECT status FROM learning_items WHERE id = ?", (pending_id,))[0][0], "pending")
        # Events recorded after the backup survive the restore.
        types = self.audit_types()
        self.assertIn("content_reviewed", types)
        self.assertEqual(types[-1], "backup_restored")
        details = self.query("SELECT details FROM audit_events WHERE event_type = 'backup_restored'")[0][0]
        self.assertIn(restored["safety_backup"], details)
        # The safety backup holds the pre-restore state and passes its checks.
        self.assertTrue(backups.verify_backup(self.db, restored["safety_backup"])["ok"])
        # Every session ended, including the admin's own.
        self.request(admin, "/api/admin/backups", expected=401)
        self.request(learner, "/api/dashboard", expected=401)

    def test_T4_BR_09_restore_needs_typed_confirmation(self):
        name = backups.create_backup(self.db, "test")["file"]
        admin = self.login("admin")
        self.request(admin, f"/api/admin/backups/{name}/restore", "POST", {}, expected=400)
        self.request(admin, f"/api/admin/backups/{name}/restore", "POST", {"confirm": "yes"}, expected=400)
        self.assertNotIn("backup_restored", self.audit_types())

    def test_T4_BR_10_backup_without_an_active_admin_is_refused(self):
        connection = sqlite3.connect(self.db)
        connection.execute("UPDATE users SET is_active = 0 WHERE role = 'admin'")
        connection.commit()
        name = backups.create_backup(self.db, "test")["file"]
        connection.execute("UPDATE users SET is_active = 1 WHERE role = 'admin'")
        connection.commit()
        connection.close()
        problems = backups.verify_backup(self.db, name)["problems"]
        self.assertTrue(any(p.startswith("T4_C05") and "administrator" in p for p in problems), problems)

    def test_T4_BR_11_restore_can_be_undone_with_the_safety_backup(self):
        original = backups.create_backup(self.db, "test")["file"]
        connection = sqlite3.connect(self.db)
        connection.execute("UPDATE learning_items SET title = 'Changed after backup' WHERE id = 1")
        connection.commit()
        connection.close()
        outcome = backups.restore_backup(self.db, original, "test")
        self.assertEqual(self.query("SELECT title FROM learning_items WHERE id = 1")[0][0], "Digital Safety Foundations")
        backups.restore_backup(self.db, outcome["safety_backup"]["file"], "test")
        self.assertEqual(self.query("SELECT title FROM learning_items WHERE id = 1")[0][0], "Changed after backup")

    def test_T4_BR_12_old_backups_are_pruned(self):
        with patch.object(backups, "MAX_BACKUPS", 3):
            names = [backups.create_backup(self.db, "test")["file"] for _ in range(5)]
        remaining = sorted(p.name for p in backups.backup_dir(self.db).glob("edustream-*.db"))
        self.assertEqual(remaining, sorted(names)[-3:])
        self.assertEqual(len(list(backups.backup_dir(self.db).glob("edustream-*.json"))), 3)

    def test_T4_BR_13_file_swapped_after_listing_is_still_checked_at_restore(self):
        good = backups.create_backup(self.db, "test")["file"]
        self.assertTrue(backups.verify_backup(self.db, good)["ok"])
        # Replace the file with a different (valid SQLite) database after it was verified.
        other = backups.create_backup(self.db, "test")["file"]
        folder = backups.backup_dir(self.db)
        shutil.copyfile(folder / other, folder / good)
        connection = sqlite3.connect(folder / good)
        connection.execute("UPDATE users SET full_name = 'Swapped' WHERE id = 1")
        connection.commit()
        connection.close()
        with self.assertRaises(backups.BackupError) as raised:
            backups.restore_backup(self.db, good, "test")
        self.assertIn("T4_C03 SHA-256 digest differs from the manifest", raised.exception.problems)
        self.assertNotEqual(self.query("SELECT full_name FROM users WHERE id = 1")[0][0], "Swapped")

    def test_T4_BR_14_backup_and_restore_work_while_the_server_is_running(self):
        admin = self.login("admin")
        learner = self.login("learner")
        before = next(e for e in self.request(learner, "/api/dashboard")["items"] if e["id"] == 1)["progress_percent"]
        name = self.request(admin, "/api/admin/backups", "POST", {})["backup"]
        self.request(learner, "/api/progress", "POST", {"item_id": 1, "progress": 40 if before != 40 else 60})
        self.request(admin, f"/api/admin/backups/{name}/restore", "POST", {"confirm": name})
        learner = self.login("learner")
        dashboard = self.request(learner, "/api/dashboard")
        item = next(entry for entry in dashboard["items"] if entry["id"] == 1)
        self.assertEqual(item["progress_percent"], before)


if __name__ == "__main__":
    unittest.main()
