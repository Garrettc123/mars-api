#!/usr/bin/env python3
"""Read-only MARS wealth-loop readiness evidence. Never dispatches or performs revenue actions."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

WORKER = Path("src/nexus/sync_wealth_loop.py")


def assess(repo_root: Path) -> dict:
    """Source inspection is not approval, execution, payment or delivery evidence."""
    if not repo_root.is_dir():
        raise ValueError("repository root must exist")
    worker = repo_root / WORKER
    present = worker.is_file() and not worker.is_symlink()
    return {
        "schema_version": 1,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED",
        "purpose": "read_only_source_readiness",
        "worker_source": str(WORKER),
        "worker_source_present": present,
        "worker_state": "source_present_unverified" if present else "missing",
        "independent_approval_receipt": "not_verified",
        "stripe_paid_settlement": "not_verified",
        "tenant_authorization": "not_verified",
        "durable_dispatch_receipt": "not_verified",
        "outbound_permission": "not_verified",
        "agents_executed": 0,
        "payments_attempted": 0,
        "messages_sent": 0,
        "customer_deliveries": 0,
        "production_readiness": False,
        "reason": (
            "Worker source located; approval, credentials, signed receipts and runtime not verified."
            if present else
            "Expected wealth worker source is absent; no execution may be inferred."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    report = assess(args.repo_root)
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
