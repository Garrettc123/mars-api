"""ASGI operator authorization; does not log tokens or request bodies."""
import os
from rhns_policy import authorize

class OperatorGuard:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        values = [v.decode("latin-1") for k, v in scope.get("headers", []) if k.lower() == b"authorization"]
        allowed, status = authorize(
            scope.get("path", ""), scope.get("method", ""),
            values[0] if len(values) == 1 else None,
            os.environ.get("MARS_OPERATOR_TOKEN", ""),
        )
        if allowed:
            await self.app(scope, receive, send)
            return
        body = b'{"detail":"Operator authentication required"}' if status == 401 else b'{"detail":"Operator authentication not configured"}'
        headers = [(b"content-type", b"application/json"), (b"cache-control", b"no-store")]
        if status == 401:
            headers.append((b"www-authenticate", b"Bearer"))
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": body})
