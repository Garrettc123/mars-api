# RHNS / MARS durable runtime bridge

`mars-api` now delegates **only** `evidence-inventory` and `action-guard` tasks to the independently hosted RHNS agent runtime. A successful request must include a receipt-backed `job_id` returned by the configured backend. `GET /agent/status/{uuid}` reads the actual durable job record; there is no placeholder `running` response.

Environment, managed server-side only:
- `RHNS_TASK_BRIDGE_ENABLED=false` initially, enable only after review.
- `RHNS_RUNTIME_URL=https://<private-authenticated-host>` (TLS required).
- `RHNS_RUNTIME_TOKEN` is the independent RHNS server token, not MARS_OPERATOR_TOKEN.
- `RHNS_RUNTIME_TENANT` is an explicit single administrative tenant identifier.

Example request: `{"agent":"action-guard","capability":"verify","payload":{"tool":"read"},"idempotency_key":"manual-review-20261128-01"}`.

The RHNS host must already be configured with a durable supported backend (e.g. Firestore) and an independently supervised worker. No Vercel Function process is treated as a persistent worker. Calls to payments, email, deploy, trading, arbitrary shell and other L2/L3 capabilities are not registered here. The bridge does **not** auto-create, approve or execute them.

Release verification: fail-closed configuration, test authorization denial, submit one approved L0/L1 task, inspect the backend job and receipt chain after restart, verify tenant scope and idempotency. Do not enable by merely adding a URL.
