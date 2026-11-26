"""T1 registration and profile tests (Student 1). IDs: T1-AC-nn."""

import unittest

import server
from support import LiveServerTestCase


class AccountTests(LiveServerTestCase):
    db_name = "edustream-accounts.db"

    def setUp(self):
        super().setUp()
        server.REGISTRATION_THROTTLE.reset()

    def register(self, client, email, password="a calm river at dawn", name="Rina Sari", expected=201, **extra):
        return self.request(client, "/api/register", "POST", {"full_name": name, "email": email, "password": password, **extra}, expected)

    # Permitted use

    def test_T1_AC_01_new_learner_registers_and_is_signed_in_without_access(self):
        client = self.client()
        body = self.register(client, "rina@example.test")
        self.assertEqual(body["user"]["role"], "learner")
        dashboard = self.request(client, "/api/dashboard")
        self.assertEqual(dashboard["role"], "learner")
        self.assertIsNone(dashboard["subscription"])
        self.request(client, "/api/access/1", expected=403)  # no plan yet, so no entitlement
        with server.connect_db() as connection:
            row = connection.execute("SELECT password_hash FROM users WHERE email = 'rina@example.test'").fetchone()
        self.assertNotIn("calm river", row[0])
        events = self.audit("account_registered")
        self.assertTrue(events and "@" not in events[-1]["details"])

    def test_T1_AC_02_users_edit_only_their_own_profile(self):
        educator = self.login("educator")
        saved = self.request(educator, "/api/profile", "POST", {"full_name": "  Noah   Bennett ", "bio": "Teaches secure coding.‮"})["profile"]
        self.assertEqual(saved["full_name"], "Noah Bennett")
        self.assertEqual(saved["bio"], "Teaches secure coding.")
        learner = self.login("learner")
        mine = self.request(learner, "/api/profile")["profile"]
        self.assertEqual(mine["email"], "learner@edustream.local")
        # Extra fields cannot change identity or role.
        self.request(learner, "/api/profile", "POST", {"full_name": "Amina Clarke", "role": "admin", "id": 2, "email": "x@example.test"})
        with server.connect_db() as connection:
            amina = connection.execute("SELECT role, email FROM users WHERE id = ?", (mine["id"],)).fetchone()
            noah = connection.execute("SELECT full_name FROM users WHERE id = 2").fetchone()
        self.assertEqual(tuple(amina), ("learner", "learner@edustream.local"))
        self.assertEqual(noah[0], "Noah Bennett")
        self.request(learner, "/api/profile", "POST", {"full_name": "Amina Clarke", "bio": "learners have no bio"}, 400)

    # Prohibited use and failure cases

    def test_T1_AC_03_registration_cannot_create_privileged_roles(self):
        client = self.client()
        body = self.register(client, "sneaky@example.test", role="admin")
        self.assertEqual(body["user"]["role"], "learner")
        self.request(client, "/api/admin/audit", expected=403)
        self.request(client, "/api/content", "POST", {"title": "x"}, 403)

    def test_T1_AC_04_weak_passwords_and_bad_details_are_rejected(self):
        client = self.client()
        cases = [
            {"email": "a@example.test", "password": "short1!"},
            {"email": "b@example.test", "password": "password123"},
            {"email": "c@example.test", "password": "aaaaaaaaaaaa"},
            {"email": "dana.lee@example.test", "password": "dana.lee-2026!"},
            {"email": "not-an-email", "password": "a calm river at dawn"},
            {"email": "e@example.test", "password": "x" * 129},
            {"email": "f@example.test", "password": "a calm river at dawn", "full_name": "J"},
            {"email": "g@example.test", "password": 12345678901},
        ]
        for case in cases:
            with self.subTest(case=case):
                payload = {"full_name": "Test Person", **case}
                self.request(client, "/api/register", "POST", payload, 400)
        emails = [case["email"] for case in cases]
        with server.connect_db() as connection:
            placeholders = ",".join("?" for _ in emails)
            count = connection.execute(f"SELECT COUNT(*) FROM users WHERE email IN ({placeholders})", emails).fetchone()[0]
        self.assertEqual(count, 0)

    def test_T1_AC_05_duplicate_email_is_refused_and_existing_account_unchanged(self):
        client = self.client()
        self.register(client, "LEARNER@edustream.local", expected=409)
        self.login("learner")  # original password still works

    def test_T1_AC_06_registration_is_rate_limited_per_client(self):
        for number in range(5):
            self.register(self.client(), f"bulk{number}@example.test")
        self.register(self.client(), "bulk5@example.test", expected=429)
        self.assertEqual(self.audit("registration_throttled")[-1]["outcome"], "denied")

    def test_T1_AC_07_password_change_needs_current_password_and_ends_other_sessions(self):
        email, old = "mover@example.test", "a calm river at dawn"
        first = self.client()
        self.register(first, email, old)
        second = self.login(email=email, password=old)
        self.request(first, "/api/profile/password", "POST", {"current_password": "wrong guess here", "new_password": "a brand new phrase 7"}, 403)
        self.request(first, "/api/profile/password", "POST", {"current_password": old, "new_password": "password123"}, 400)
        self.request(first, "/api/profile/password", "POST", {"current_password": old, "new_password": "a brand new phrase 7"})
        self.request(first, "/api/profile")              # the session that changed it stays signed in
        self.request(second, "/api/profile", expected=401)  # every other session ended
        self.request(self.client(), "/api/login", "POST", {"email": email, "password": old}, 401)
        self.login(email=email, password="a brand new phrase 7")
        self.assertTrue(self.audit("password_change_failed"))
        self.assertIn("Other sessions ended: 1", self.audit("password_changed")[-1]["details"])

    def test_T1_AC_08_profile_requires_sign_in(self):
        anonymous = self.client()
        self.request(anonymous, "/api/profile", expected=401)
        self.request(anonymous, "/api/profile", "POST", {"full_name": "Nobody Here"}, 401)


if __name__ == "__main__":
    unittest.main()
