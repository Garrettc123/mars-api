"""Regression: no public deployment entrypoint bypasses operator authorization."""
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
import main
import guarded_main
from rhns_middleware import OperatorGuard


class ProtectedEntrypointTests(unittest.TestCase):
    def test_both_exports_are_same_authorized_asgi_app(self):
        self.assertIs(main.app, guarded_main.app)
        self.assertIsInstance(main.app, OperatorGuard)

    def test_no_configured_token_denies_sensitive_endpoints(self):
        paths = ("/invoice/create", "/payment/link", "/lead/capture",
                 "/deal/submit", "/agent/run", "/notify")
        with patch.dict(os.environ, {"MARS_OPERATOR_TOKEN": ""}):
            with TestClient(main.app) as client:
                for path in paths:
                    with self.subTest(path=path):
                        response = client.post(path, json={})
                        self.assertEqual(response.status_code, 503)
                        self.assertEqual(response.headers.get("cache-control"), "no-store")

    def test_configured_operator_token_does_not_make_routes_public(self):
        token = "guard-" + "x" * 36
        with patch.dict(os.environ, {"MARS_OPERATOR_TOKEN": token}):
            with TestClient(guarded_main.app) as client:
                self.assertEqual(client.get("/deal/list").status_code, 401)
                self.assertEqual(client.post("/invoice/create", json={}).status_code, 401)
                self.assertEqual(client.post("/notify", json={},
                                             headers={"Authorization": "Bearer wrong"}).status_code, 401)

    def test_health_remains_public_and_invalid_stripe_signature_is_rejected(self):
        with patch.dict(os.environ, {"MARS_OPERATOR_TOKEN": ""}):
            with TestClient(main.app) as client:
                self.assertEqual(client.get("/health").status_code, 200)
                response = client.post("/webhook/stripe", data=b"not-an-event",
                                       headers={"stripe-signature": "invalid"})
                self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
