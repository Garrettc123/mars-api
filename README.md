# MARS API

MARS API is the commercial API surface for Garcar Enterprise’s metacognitive reasoning system. It is designed for teams that need higher-confidence AI behavior, better uncertainty awareness, and a production-ready endpoint for enterprise integration.

## What it does

MARS API helps software, automation, and enterprise operations teams:
- score uncertainty before acting
- route high-risk requests for deeper reasoning
- expose reasoning services through a simple API
- support production deployment with standard Python service tooling

## Ideal users

MARS API is built for:
- engineering teams integrating AI into products
- internal automation platforms
- enterprise workflow systems
- founders validating premium AI infrastructure offers

## Current repo contents

This repository already includes:
- `main.py` for the application logic
- `Procfile` for deploy process definition
- `requirements.txt` for dependencies
- `.github/` for workflow automation

## Deployment

The repo is structured for cloud deployment on platforms such as Render or Railway.

Typical start pattern:
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Environment variables
- `STRIPE_SECRET_KEY` – Stripe secret key for revenue endpoints
- `STRIPE_WEBHOOK_SECRET` – Stripe webhook signing secret
- `ZAPIER_WEBHOOK_URL` – optional Zapier webhook for event fan-out

### Key endpoints
- `GET /` – service status & endpoint list
- `GET /health` – health check
- `GET /revenue/dashboard` – live Stripe revenue snapshot
- `POST /lead/capture` – lead intake
- `POST /invoice/create` – create & finalize Stripe invoice
- `POST /payment/link` – generate Stripe payment link
- `POST /deal/submit` – deal desk submission
- `POST /agent/run` – queue agent task
- `POST /webhook/stripe` – Stripe webhook receiver

---
*Garcar Enterprise — MARS (Multi-Agent Revenue System)*
