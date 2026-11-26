"""Billing failure (T1), takedown (T2) and operations view (T4) tests. IDs: T1-PAY-nn, T2-TD-nn, T4-OP-nn."""

import unittest

import operations
import server
from support import LiveServerTestCase


class OperationsTests(LiveServerTestCase):
    db_name = "edustream-operations.db"

    def setUp(self):
        super().setUp()
        with server.connect_db() as connection:
            # Each test starts from a clean audit and billing history for the demo learner.
            connection.execute("DELETE FROM audit_events")
            connection.execute("DELETE FROM payments WHERE status = 'failed'")
            connection.commit()

    def plan_id(self, code):
        with server.connect_db() as connection:
            return connection.execute("SELECT id FROM plans WHERE code = ?", (code,)).fetchone()[0]

    def active_plan(self):
        with server.connect_db() as connection:
            return server.active_subscription(connection, 1)["plan_code"]

    def issues(self, admin, kind=None):
        found = self.request(admin, "/api/admin/operations")["issues"]
        return [issue for issue in found if kind is None or issue["kind"] == kind]

    # T1: simulated payment failure

    def test_T1_PAY_01_declined_test_card_records_failure_and_keeps_plan(self):
        learner = self.login("learner")
        before = self.active_plan()
        body = self.request(learner, "/api/subscription", "POST",
                            {"plan_id": self.plan_id("plus"), "confirm": True, "payment_method": "test-card-decline"}, 402)
        self.assertIn("declined", body["error"])
        self.assertEqual(self.active_plan(), before)
        self.request(learner, "/api/access/3", expected=403)  # Plus course still locked
        payments = self.request(learner, "/api/dashboard")["payments"]
        self.assertEqual(payments[0]["status"], "failed")
        self.assertEqual(self.audit("payment_failed")[-1]["outcome"], "failure")
        self.request(learner, "/api/subscription", "POST", {"plan_id": self.plan_id("plus"), "confirm": True, "payment_method": "test-card-approve"})
        self.assertEqual(self.active_plan(), "plus")
        self.request(learner, "/api/subscription", "POST", {"plan_id": self.plan_id("starter"), "confirm": True})

    def test_T1_PAY_02_only_simulated_payment_methods_are_accepted(self):
        learner = self.login("learner")
        for method in ("4111111111111111", "real-card", 7):
            self.request(learner, "/api/subscription", "POST", {"plan_id": self.plan_id("plus"), "confirm": True, "payment_method": method}, 400)

    # T2: admin takedown and review notes

    def test_T2_TD_01_takedown_hides_item_from_learners_with_a_recorded_reason(self):
        admin, learner, educator = self.login("admin"), self.login("learner"), self.login("educator")
        item_id = self.request(educator, "/api/content", "POST", {
            "title": "Phishing Drill Notes", "category": "Cybersecurity", "content_type": "article", "language": "en",
            "duration_minutes": 20, "description": "Synthetic notes describing a phishing awareness drill.",
        })["item_id"]
        self.request(admin, f"/api/admin/content/{item_id}/review", "POST", {"decision": "approved", "note": "Checked against the brief."})
        reviewed = self.audit("content_reviewed")[-1]["details"]
        self.assertIn("pending -> approved", reviewed)
        self.assertIn("Checked against the brief.", reviewed)
        published = [item["id"] for item in self.request(admin, "/api/dashboard")["published_items"]]
        self.assertIn(item_id, published)
        self.request(admin, f"/api/admin/content/{item_id}/takedown", "POST", {"reason": "no"}, 400)
        self.request(learner, f"/api/admin/content/{item_id}/takedown", "POST", {"reason": "Learners should not do this"}, 403)
        self.request(admin, f"/api/admin/content/{item_id}/takedown", "POST", {"reason": "Contains an outdated   phishing example"})
        event = self.audit("content_taken_down")[-1]
        self.assertIn("approved -> rejected", event["details"])
        self.assertIn("reason: Contains an outdated phishing example", event["details"])
        self.request(admin, f"/api/admin/content/{item_id}/takedown", "POST", {"reason": "Second attempt"}, 409)
        self.request(admin, "/api/admin/content/99999/takedown", "POST", {"reason": "Missing item"}, 404)
        self.request(learner, f"/api/access/{item_id}", expected=403)

    # T4: operations view and seeded problems

    def test_T4_OP_01_seeded_payment_problem_appears_and_clears_after_fix(self):
        admin = self.login("admin")
        self.assertEqual(self.issues(admin, "payment_failed"), [])
        operations.seed_problem(server.DB_PATH, "payment")
        issue = self.issues(admin, "payment_failed")[0]
        self.assertEqual(issue["severity"], "high")
        self.assertEqual(issue["event_type"], "payment_failed")
        self.assertTrue(self.request(admin, "/api/admin/audit?event_type=payment_failed")["events"])
        self.assertTrue(self.audit("problem_seeded"))
        learner = self.login("learner")
        self.request(learner, "/api/subscription", "POST", {"plan_id": self.plan_id("starter"), "confirm": True})
        self.assertEqual(self.issues(admin, "payment_failed"), [])

    def test_T4_OP_02_burst_of_denied_requests_is_flagged_per_account(self):
        admin, learner = self.login("admin"), self.login("learner")
        for _ in range(operations.DENIED_BURST_THRESHOLD - 1):
            self.request(learner, "/api/access/3", expected=403)
        self.assertEqual(self.issues(admin, "denied_burst"), [])
        self.request(learner, "/api/access/3", expected=403)
        issue = self.issues(admin, "denied_burst")[0]
        self.assertEqual(issue["user_id"], 1)
        traced = self.request(admin, "/api/admin/audit?user_id=1&outcome=denied")["events"]
        self.assertGreaterEqual(len(traced), operations.DENIED_BURST_THRESHOLD)
        self.request(learner, "/api/admin/operations", expected=403)

    def test_T4_OP_03_seeded_suspicious_content_is_flagged_and_cleared_by_takedown(self):
        admin = self.login("admin")
        operations.seed_problem(server.DB_PATH, "content")
        issue = self.issues(admin, "suspicious_content")[0]
        self.request(admin, f"/api/admin/content/{issue['item_id']}/takedown", "POST", {"reason": "Seeded suspicious link and script"})
        self.assertEqual(self.issues(admin, "suspicious_content"), [])

    def test_T4_OP_04_analytics_summary_reports_plans_payments_and_courses(self):
        admin = self.login("admin")
        operations.seed_problem(server.DB_PATH, "access")
        analytics = self.request(admin, "/api/admin/operations")["analytics"]
        plans = {row["plan"]: row["active_subscriptions"] for row in analytics["plans"]}
        self.assertGreaterEqual(plans["Starter"], 1)
        self.assertIn("paid", analytics["payments_30_days"])
        titles = [course["title"] for course in analytics["courses"]]
        self.assertIn("Digital Safety Foundations", titles)
        denied = {row["event_type"]: row["count"] for row in analytics["denied_7_days"]}
        self.assertGreaterEqual(denied["access_denied"], operations.DENIED_BURST_THRESHOLD + 1)

    def test_T4_OP_05_seed_problem_rejects_unknown_kinds(self):
        with self.assertRaises(ValueError):
            operations.seed_problem(server.DB_PATH, "everything")


if __name__ == "__main__":
    unittest.main()
