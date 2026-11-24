# MARS Wealth Loop: execution is not verified

The previous hourly workflow printed claims that RHNS approval was verified,
that the wealth loop executed, and that an event was dispatched. Those claims
were unsupported when the referenced worker file was absent.

The replacement workflow named **NEXUS Wealth Loop Readiness (read-only)**
performs only source assessment. Its green job status means the assessment ran
correctly, **not** that an agent executed, money was earned, a charge cleared,
or an outbound event was delivered.

## Local verification

    python -m unittest -v test_wealth_readiness
    python scripts/wealth_loop_readiness.py --repo-root . --output /tmp/wealth-readiness.json

The JSON reports a BLOCKED operating status even if the expected worker file
is later added. It never loads provider credentials, imports or executes that
worker, forwards GitHub dispatch payloads, or sends network requests.

## Full execution release requirements

- The actual worker implementation must exist, pass tests and be bound to a reviewed, pinned source commit.
- A tenant-scoped, signed RHNS authorization for the **exact action** must be
  independently verified and not expired or replayed.
- Payment settlement must be verified from the authorized Stripe account using
  correctly scoped credentials before any fulfillment claims.
- Persist idempotent dispatch and outcome receipts; uncertain outcomes remain
  blocked until reconciled.
- Any outgoing email, CRM mutation, or other third-party action requires
  appropriate consent, explicit permitted scope, and a traceable approval.
- A separate release pipeline must be implemented and verified before turning
  on live execution. This monitoring workflow is never itself an approval.

This repository does not prove revenue, operating agents, or hosted readiness
merely because its GitHub Action returned success.
