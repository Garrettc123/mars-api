"""Fail-closed authorization policy; no network or billing side effects."""
import hmac

PUBLIC_PATHS = frozenset({"/", "/health", "/webhook/stripe"})

def authorize(path, method, authorization, configured_token):
    """Return (allowed, HTTP status). Stripe signature verification stays mandatory.

    Public exceptions are exact: GET /, GET /health, POST /webhook/stripe.
    All other requests require a configured operator bearer token.
    """
    if (method == "GET" and path in {"/", "/health"}) or (
        method == "POST" and path == "/webhook/stripe"
    ):
        return True, 200
    if not configured_token or len(configured_token) < 32:
        return False, 503
    scheme, separator, supplied = (authorization or "").partition(" ")
    if not separator or scheme.lower() != "bearer" or not supplied:
        return False, 401
    if not hmac.compare_digest(supplied.encode("utf-8"), configured_token.encode("utf-8")):
        return False, 401
    return True, 200
