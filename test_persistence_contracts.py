"""Only acknowledge MARS lead/deal writes when the database confirms the row."""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
import main


class Storage:
    def __init__(self, outcome="confirmed"):
        self.outcome = outcome
        self.rows = []

    def table(self, name):
        self.table_name = name
        return self

    def insert(self, row):
        self.rows.append(row)
        return self

    def execute(self):
        if self.outcome == "raises":
            raise OSError("isolated storage failure")
        if self.outcome == "unknown":
            return SimpleNamespace(data=[])
        return SimpleNamespace(data=[dict(self.rows[-1])])


class DurableIngressTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {"MARS_OPERATOR_TOKEN": "x" * 48})
        self.environment.start()
        self.client = TestClient(main.app)
        self.client.__enter__()
        self.headers = {"Authorization": "Bearer " + "x" * 48}

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.environment.stop()

    def post(self, path, payload):
        return self.client.post(path, json=payload, headers=self.headers)

    def test_lead_without_consent_denied_before_storage(self):
        with patch.object(main, "get_supabase") as storage:
            r = self.post("/lead/capture", {
                "name": "Buyer", "email": "buyer@example.org", "consentGiven": False
            })
            self.assertEqual(r.status_code, 422)
            storage.assert_not_called()

    def test_lead_without_db_returns_503(self):
        with patch.object(main, "get_supabase", return_value=None):
            r = self.post("/lead/capture", {
                "name": "Buyer", "email": "buyer@example.org", "consentGiven": True
            })
            self.assertEqual(r.status_code, 503)

    def test_failed_or_unknown_lead_insert_cannot_claim_success(self):
        for outcome in ("raises", "unknown"):
            with self.subTest(outcome=outcome):
                with patch.object(main, "get_supabase", return_value=Storage(outcome)):
                    r = self.post("/lead/capture", {
                        "name": "Buyer", "email": "buyer@example.org",
                        "consentGiven": True
                    })
                    self.assertEqual(r.status_code, 503)

    def test_confirmed_lead_is_stored_without_fanout_or_pii_echo(self):
        store = Storage()
        with patch.object(main, "get_supabase", return_value=store), \
             patch.object(main, "fire_webhooks", new_callable=AsyncMock) as fanout:
            r = self.post("/lead/capture", {
                "name": "Buyer", "email": "buyer@example.org",
                "consentGiven": True, "source": "test"
            })
            self.assertEqual(r.status_code, 200, r.text)
            data = r.json()
            self.assertEqual(data["status"], "stored")
            self.assertFalse(data["outbound_sent"])
            self.assertEqual(store.rows[0]["id"], data["id"])
            self.assertNotIn("buyer@example.org", r.text)
            fanout.assert_not_awaited()

    def test_deal_requires_company_and_email(self):
        with patch.object(main, "get_supabase") as storage:
            r = self.post("/deal/submit", {"company": "", "email": "buyer@example.org"})
            self.assertEqual(r.status_code, 422)
            storage.assert_not_called()

    def test_deal_missing_or_unknown_storage_fails_closed(self):
        body = {"company": "Sample Contractor", "email": "buyer@example.org"}
        for db in (None, Storage("raises"), Storage("unknown")):
            with self.subTest(db=db), patch.object(main, "get_supabase", return_value=db):
                self.assertEqual(self.post("/deal/submit", body).status_code, 503)

    def test_confirmed_deal_does_not_claim_outreach(self):
        store = Storage()
        with patch.object(main, "get_supabase", return_value=store), \
             patch.object(main, "fire_webhooks", new_callable=AsyncMock) as fanout:
            r = self.post("/deal/submit", {
                "company": "Sample Contractor", "email": "buyer@example.org"
            })
            self.assertEqual(r.status_code, 200, r.text)
            self.assertEqual(r.json()["status"], "stored")
            self.assertFalse(r.json()["outbound_sent"])
            self.assertEqual(store.rows[0]["id"], r.json()["deal_id"])
            fanout.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
