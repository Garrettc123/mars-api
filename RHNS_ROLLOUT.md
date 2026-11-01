# RHNS production rollout and acceptance

## Current scope
Operator authorization is implemented by guarded_main:app. Launching main:app bypasses the wrapper. This is a shared operator credential, not customer authentication, tenant isolation, or a complete entitlement system.

## Hosting configuration
1. Select the mars-api service and intended environment.
2. Store a cryptographically random token of at least 32 characters as MARS_OPERATOR_TOKEN in the hosting secret store. Never commit it or send it in chat.
3. Start command: uvicorn guarded_main:app --host 0.0.0.0 --port $PORT
4. Use /health for liveness, not proof of authorization, database, payment, or execution readiness.
5. Update trusted server-side clients to send Authorization: Bearer followed by the token. Never expose the shared operator credential in browser code.
6. Verify the actual deployed commit and start command in hosting logs.

## Acceptance
- GET /health without credentials: 200.
- Protected reads without credentials: 401 with a configured token, 503 with missing or short configuration.
- GET /openapi.json with valid credentials: 200.
- Incorrect token: 401.
- Verify Stripe signatures separately in test mode.
- Never use live invoice, payment-link, or notification creation as smoke tests.

## Known limits
Public root and health routes retain operational metadata. Anonymous lead capture is now protected. Cross-origin unauthenticated preflights and WebSockets are denied. Hard-coded agent status and swallowed persistence/delivery failures remain unresolved. Purchase entitlements, a durable task ledger, customer metering, and revenue reconciliation are not implemented by this patch. Verification CI does not gate the existing deploy workflow or host auto-deploy.

## Recovery
Repair secret configuration or authorized clients instead of bypassing the guard. If the guarded build cannot start, restore a known tested guarded release or pause affected service pending a reviewed repair.

## Completion evidence
Record deployed commit, CI run result, hosting deployment result, tested URL, timestamp, and redacted HTTP statuses. Never log credentials. Do not claim production readiness or collected revenue without supporting records.
