"""Guarded RHNS runtime bridge: L0/L1 only; no external actions.

The remote runtime must use durable storage and an independently supervised worker.
No job is declared queued without a returned remote job ID.
"""
from __future__ import annotations

import os
import re
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException

_ALLOWED = {
    "evidence-inventory": frozenset({"observe", "analyze"}),
    "action-guard": frozenset({"analyze", "verify"}),
}
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
_JOB_ID = re.compile(r"^(?:[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|[0-9a-fA-F]{64})$")


def _configuration() -> tuple[str, str, str]:
    if os.getenv("RHNS_TASK_BRIDGE_ENABLED", "").lower() != "true":
        raise HTTPException(status_code=503, detail="RHNS task bridge disabled")
    base = os.getenv("RHNS_RUNTIME_URL", "").rstrip("/")
    token = os.getenv("RHNS_RUNTIME_TOKEN", "")
    tenant = os.getenv("RHNS_RUNTIME_TENANT", "")
    parts = urlsplit(base)
    if (parts.scheme != "https" or not parts.netloc or parts.username or parts.password
            or parts.query or parts.fragment or parts.path not in ("", "/")
            or len(token) < 24 or not _IDENTIFIER.fullmatch(tenant)):
        raise HTTPException(status_code=503, detail="RHNS durable runtime is not configured")
    return base, token, tenant


def _task_fields(data: dict) -> dict:
    agent = data.get("agent")
    capability = data.get("capability")
    payload = data.get("payload")
    key = data.get("idempotency_key")
    if set(data) != {"agent", "capability", "payload", "idempotency_key"}:
        raise HTTPException(status_code=422, detail="Only explicit RHNS task fields are permitted")
    if not isinstance(agent, str) or not isinstance(capability, str) or agent not in _ALLOWED or capability not in _ALLOWED[agent]:
        raise HTTPException(status_code=403, detail="RHNS capability is not allowed")
    if not isinstance(payload, dict) or not isinstance(key, str) or not _IDENTIFIER.fullmatch(key) or len(key) < 16:
        raise HTTPException(status_code=422, detail="Bounded payload and idempotency key required")
    import json
    try:
        body = json.dumps(payload, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid JSON payload") from exc
    if len(body) > 64 * 1024:
        raise HTTPException(status_code=413, detail="Payload too large")
    return {"agent": agent, "capability": capability, "payload": payload, "idempotency_key": key}


async def _remote(method: str, path: str, data: dict | None = None) -> dict:
    base, token, _ = _configuration()
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=False, trust_env=False) as client:
            response = await client.request(method, base + path,
                                            headers={"Authorization": "Bearer " + token},
                                            json=data)
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="RHNS job not found")
        if response.status_code not in (200, 202):
            raise HTTPException(status_code=502, detail="RHNS runtime rejected operation")
        result = response.json()
        if not isinstance(result, dict):
            raise ValueError("non-object response")
        return result
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="RHNS runtime unavailable") from exc


async def submit_bounded_task(data: dict) -> dict:
    fields = _task_fields(data)
    _, _, tenant = _configuration()
    result = await _remote("POST", "/tasks", {"tenant": tenant, **fields})
    if not isinstance(result.get("job_id"), str) or result.get("state") not in (
            "queued", "retry_wait", "running", "succeeded", "failed",
            "outcome_unknown", "cancelled"):
        raise HTTPException(status_code=502, detail="RHNS task acknowledgment invalid")
    return {"job_id": result["job_id"], "state": result["state"],
            "idempotent_replay": result.get("idempotent_replay") is True,
            "source": "rhns_runtime_durable"}


async def get_bounded_task(job_id: str) -> dict:
    if not _JOB_ID.fullmatch(job_id):
        raise HTTPException(status_code=422, detail="Invalid RHNS job ID")
    result = await _remote("GET", "/jobs/" + job_id)
    if result.get("job_id") != job_id or not isinstance(result.get("state"), str):
        raise HTTPException(status_code=502, detail="RHNS job receipt invalid")
    return result
