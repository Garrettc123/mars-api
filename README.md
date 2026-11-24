# MARS API

MARS API is the commercial API surface for Garcar Enterprise’s metacognitive reasoning system. It is designed for teams that need higher-confidence AI behavior, better uncertainty awareness, and a proposed enterprise integration endpoint; production readiness requires live authorization, persistence and deployment verification.

**Source version 2.1.1** — code-level integration candidate. Installed credentials, deployment and financial outcomes have not been verified by this README.

## What it does

MARS API helps software, automation, and enterprise operations teams:
- score uncertainty before acting
- route high-risk requests for deeper reasoning
- expose reasoning services through a simple API
- support production deployment with standard Python service tooling
- capture leads, create invoices/payment links, and surface live Stripe revenue

## Ideal users

MARS API is built for:
- engineering teams integrating AI into products
- internal automation platforms
- enterprise workflow systems
- founders validating premium AI infrastructure offers

## Current repo contents

- `main.py` — application logic (v2.1.0)
- `Procfile` — deploy process definition
- `requirements.txt` — dependencies
- `.env.example` — canonical key template
- `.github/` — workflow automation

## Deployment

Structured for Render, Railway, or any platform that respects `Procfile`.

```bash
uvicorn guarded_main:app --host 0.0.0.0 --port $PORT
```

### Canonical environment variables

These names are shared across the entire Garcar stack. Set them once in Railway / GitHub Actions / vault and every service (including MARS) can consume them.

| Key | Plane | Required for |
|-----|-------|--------------|
| `STRIPE_SECRET_KEY` | Payment | Revenue dashboard, invoices, payment links |
| `STRIPE_WEBHOOK_SECRET` | Payment | `/webhook/stripe` signature verification |
| `STRIPE_PUBLISHABLE_KEY` | Payment | Client-side (optional) |
| `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` | Shared App | Persistent leads & deals |
| `ZAPIER_WEBHOOK_URL` | Fan-out | Event bridge |
| `SLACK_WEBHOOK_URL` | Fan-out | Slack notifications |
| `ORCHESTRATOR_WEBHOOK_URL` (or `MARS_WEBHOOK_URL`) | Fan-out | Master orchestrator |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | AI | Future agent reasoning |
| `LINEAR_API_KEY` / `LINEAR_TEAM_ID` | Orchestration | Task routing |
| `GITHUB_TOKEN` | Orchestration | Repo automation |
| `APP_URL` / `APP_BASE_URL` | Shared | Public base URL |

See `.env.example` and `systems-master-hub/vault/.vault.env.template` for the full enterprise matrix.

### Authorization and release boundaries

The `main:app` and `guarded_main:app` exports now share the **same operator authorization guard**. Public access is limited to `GET /`, `GET /health`, and the Stripe webhook signature-verification ingress. All other endpoints require an independently provisioned strong `MARS_OPERATOR_TOKEN`; with no configured token they return HTTP 503. No token values are returned by health checks.

The GitHub workflow validates code only; it **does not deploy to Railway or send completion emails**. This is intentional. Lead/deal durability, verified revenue reporting, payment authorization and external fan-out remain separate release blockers; presence of environment-variable names is not evidence they work.

### Key endpoints

- `GET /` — service status & endpoint list
- `GET /health` — health + key-status matrix (values never returned)
- `GET /revenue/dashboard` — live Stripe revenue snapshot
- `POST /lead/capture` — lead intake (persists to Supabase when configured)
- `POST /invoice/create` — create & finalize Stripe invoice
- `POST /payment/link` — generate Stripe payment link
- `POST /deal/submit` — deal desk submission
- `GET /deal/list` — list deals (Supabase-backed)
- `POST /agent/run` — queue agent task
- `POST /webhook/stripe` — Stripe webhook receiver
- `POST /notify` — notification fan-out

---
*Garcar Enterprise — MARS (Multi-Agent Revenue System) · canonical keys enabled*


### Lead and deal persistence boundary

The protected `POST /lead/capture` and `POST /deal/submit` routes now refuse
to acknowledge an intake unless an authorized Supabase client is configured
and its insert response contains the exact generated row ID. Missing,
failed, or ambiguous persistence returns **HTTP 503**; invalid input or
missing explicit lead consent returns **HTTP 422**. An HTTP 200 response
confirms a represented row insert only, not customer outreach, qualified
revenue, or complete disaster recovery.

These two routes no longer broadcast submitted customer fields to
Slack, Zapier, or the orchestrator merely because intake occurred. Buyer data
must not be copied to external systems without reviewed scope and consent.
Source code does not establish live Supabase ownership or database health.

Before production use, verify the actual project schema, tenant access,
idempotency/duplicate prevention, private-data retention, consent records,
backup/restore, and customer-approved delivery integrations. An uncertain
database acknowledgement may need manual reconciliation before retrying.
