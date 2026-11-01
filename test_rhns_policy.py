import unittest
from rhns_policy import authorize

class AuthorizationTests(unittest.TestCase):
    token = "x" * 40

    def test_public_health(self):
        self.assertEqual(authorize("/health", "GET", None, ""), (True, 200))

    def test_stripe_signature_route_preserved(self):
        self.assertEqual(authorize("/webhook/stripe", "POST", None, ""), (True, 200))

    def test_missing_configuration_fails_closed(self):
        self.assertEqual(authorize("/invoice/create", "POST", None, ""), (False, 503))

    def test_short_token_fails_closed(self):
        self.assertEqual(authorize("/agent/run", "POST", "Bearer short", "short"), (False, 503))

    def test_unauthenticated_protected_routes(self):
        for path in ("/invoice/create", "/payment/link", "/deal/list", "/agent/run", "/api/reason", "/docs", "/openapi.json"):
            with self.subTest(path=path):
                self.assertEqual(authorize(path, "POST", None, self.token), (False, 401))

    def test_valid_token(self):
        self.assertEqual(authorize("/agent/run", "POST", "Bearer " + self.token, self.token), (True, 200))

    def test_wrong_token(self):
        self.assertEqual(authorize("/agent/run", "POST", "Bearer wrong", self.token), (False, 401))

    def test_prefix_is_not_public(self):
        self.assertEqual(authorize("/health/private", "GET", None, self.token), (False, 401))

    def test_public_path_wrong_method(self):
        self.assertEqual(authorize("/health", "POST", None, self.token), (False, 401))

    def test_scheme_case_insensitive(self):
        self.assertEqual(authorize("/agent/run", "POST", "bearer " + self.token, self.token), (True, 200))

    def test_unicode_input_denied_without_error(self):
        self.assertEqual(authorize("/agent/run", "POST", "Bearer \u2603", self.token), (False, 401))

if __name__ == "__main__":
    unittest.main()
