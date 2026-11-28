"""Contract tests: no fake jobs or unauthorized side effects."""
import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

import main

TOKEN = "operator-" + "x" * 40

class RuntimeBridgeTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "MARS_OPERATOR_TOKEN": TOKEN,
            "RHNS_TASK_BRIDGE_ENABLED": "false",
            "RHNS_RUNTIME_URL": "",
            "RHNS_RUNTIME_TOKEN": "",
            "RHNS_RUNTIME_TENANT": ""
        })
        self.env.start()
        self.client = TestClient(main.app)
        self.client.__enter__()
        self.auth = {"Authorization": "Bearer " + TOKEN}

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.env.stop()

    def test_no_fabricated_job_without_durable_runtime(self):
        response = self.client.post("/agent/run", headers=self.auth, json={
            "agent": "action-guard", "capability": "verify",
            "payload": {"tool": "read"}, "idempotency_key": "test-safely-unique-key"
        })
        self.assertEqual(response.status_code, 503)

    def test_no_fake_status(self):
        response = self.client.get("/agent/status/11111111-1111-4111-8111-111111111111", headers=self.auth)
        self.assertEqual(response.status_code, 503)

    def test_unregistered_capability_blocked(self):
        response = self.client.post("/agent/run", headers=self.auth, json={
            "agent": "trader", "capability": "trade",
            "payload": {}, "idempotency_key": "test-safely-unique-key"
        })
        self.assertEqual(response.status_code, 403)

    def test_malformed_agent_blocked(self):
        response = self.client.post("/agent/run", headers=self.auth, json={
            "agent": [], "capability": "verify",
            "payload": {}, "idempotency_key": "test-safely-unique-key"
        })
        self.assertEqual(response.status_code, 403)

    def test_invalid_job_id_blocked(self):
        response = self.client.get("/agent/status/../../unsafe", headers=self.auth)
        self.assertIn(response.status_code, (404, 422))

    def test_bridge_needs_tls_and_valid_secret(self):
        from rhns_runtime_client import _configuration
        from fastapi import HTTPException
        with patch.dict(os.environ, {
            "RHNS_TASK_BRIDGE_ENABLED": "true",
            "RHNS_RUNTIME_URL": "http://example.com",
            "RHNS_RUNTIME_TOKEN": "x" * 32,
            "RHNS_RUNTIME_TENANT": "garcar"
        }):
            with self.assertRaises(HTTPException) as error:
                _configuration()
            self.assertEqual(error.exception.status_code, 503)

if __name__ == "__main__":
    unittest.main()
