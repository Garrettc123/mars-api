"""Shared MARS v1.1 reason client. HTTP to mars-production when configured."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def reason(query: str, route: Optional[str] = None, max_tokens: Optional[int] = None) -> Dict[str, Any]:
    base = (os.getenv("MARS_REASON_URL") or os.getenv("MARS_PRODUCTION_URL") or "").rstrip("/")
    key = os.getenv("MARS_API_KEY") or ""
    payload = {"query": query}
    if route:
        payload["route"] = route
    if max_tokens:
        payload["max_tokens"] = max_tokens

    if not base:
        return {
            "success": False,
            "queued": True,
            "reasoning": "",
            "model": None,
            "route": {
                "path": "queued",
                "reason": "mars_reason_url_unset",
                "escalated": False,
                "score_version": "conf-re-v1.1",
            },
            "timestamp": _now(),
        }

    url = f"{base}/api/reason"
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if key:
        headers["X-Api-Key"] = key
    req = Request(url, data=body, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode())
        data.setdefault("success", True)
        data.setdefault("timestamp", _now())
        return data
    except HTTPError as exc:
        return {
            "success": False,
            "error": f"http_{exc.code}",
            "reasoning": "",
            "route": {"path": "error", "reason": "upstream_http", "escalated": False},
            "timestamp": _now(),
        }
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {
            "success": False,
            "error": exc.__class__.__name__,
            "reasoning": "",
            "route": {"path": "error", "reason": "upstream_unreachable", "escalated": False},
            "timestamp": _now(),
        }


def status() -> Dict[str, Any]:
    base = (os.getenv("MARS_REASON_URL") or os.getenv("MARS_PRODUCTION_URL") or "").rstrip("/")
    if not base:
        return {"wired": False, "version": "1.1.0", "reason": "mars_reason_url_unset"}
    req = Request(f"{base}/api/status", method="GET")
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        data["wired"] = True
        return data
    except Exception as exc:
        return {"wired": True, "reachable": False, "error": exc.__class__.__name__}
