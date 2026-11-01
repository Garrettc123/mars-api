import unittest
from unittest.mock import patch
from rhns_middleware import OperatorGuard

class GuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_cases(self):
        token = "x" * 40
        cases = [
            ("GET", "/health", [], "", 204),
            ("POST", "/webhook/stripe", [], "", 204),
            ("POST", "/agent/run", [], "", 503),
            ("POST", "/agent/run", [], token, 401),
            ("POST", "/agent/run", [(b"authorization", b"Bearer " + token.encode())], token, 204),
            ("POST", "/agent/run", [(b"authorization", b"Bearer bad")], token, 401),
            ("GET", "/health/private", [], token, 401),
            ("OPTIONS", "/agent/run", [], token, 401),
            ("GET", "/deal/list", [(b"authorization", b"Bearer " + token.encode())] * 2, token, 401),
        ]
        for method, path, headers, configured, expected in cases:
            with self.subTest(method=method, path=path, expected=expected):
                calls, messages = [], []
                async def downstream(scope, receive, send):
                    calls.append(path)
                    await send({"type": "http.response.start", "status": 204, "headers": []})
                    await send({"type": "http.response.body", "body": b""})
                async def receive():
                    return {"type": "http.request", "body": b"", "more_body": False}
                async def send(message):
                    messages.append(message)
                with patch.dict("os.environ", {"MARS_OPERATOR_TOKEN": configured}):
                    await OperatorGuard(downstream)({"type": "http", "method": method, "path": path, "headers": headers}, receive, send)
                self.assertEqual(messages[0]["status"], expected)
                self.assertEqual(bool(calls), expected == 204)

    async def test_websocket_denied(self):
        messages = []
        async def downstream(*args):
            self.fail("WebSocket reached downstream")
        async def send(message):
            messages.append(message)
        await OperatorGuard(downstream)({"type": "websocket"}, None, send)
        self.assertEqual(messages, [{"type": "websocket.close", "code": 1008}])

if __name__ == "__main__":
    unittest.main()
