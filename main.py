from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import stripe, os, httpx
from datetime import datetime
from typing import Optional, Any

# ── Canonical Garcar Enterprise keys (from systems-master-hub vault + AutoKey) ─
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
ZAPIER_WEBHOOK_URL = os.getenv("ZAPIER_WEBHOOK_URL", "")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
ORCHESTRATOR_WEBHOOK_URL = os.getenv("ORCHESTRATOR_WEBHOOK_URL", "") or os.getenv("MARS_WEBHOOK_URL", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "") or os.getenv("SUPABASE_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LINEAR_API_KEY = os.getenv("LINEAR_API_KEY", "")
LINEAR_TEAM_ID = os.getenv("LINEAR_TEAM_ID", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
APP_URL = os.getenv("APP_URL", "") or os.getenv("APP_BASE_URL", "")

app = FastAPI(
    title="MARS API",
    version="2.1.0",
    description="Garcar Enterprise metacognitive revenue & reasoning surface — canonical key aligned"
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

stripe.api_key = STRIPE_SECRET_KEY

# Optional Supabase client (lazy)
_supabase = None

def get_supabase():
    global _supabase
    if _supabase is not None:
        return _supabase
    if SUPABASE_URL and SUPABASE_SERVICE_KEY:
        try:
            from supabase import create_client
            _supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
            return _supabase
        except Exception:
            return None
    return None

def key_status() -> dict:
    """Report which canonical keys are present (never the values)."""
    return {
        "STRIPE_SECRET_KEY": bool(STRIPE_SECRET_KEY),
        "STRIPE_WEBHOOK_SECRET": bool(STRIPE_WEBHOOK_SECRET),
        "STRIPE_PUBLISHABLE_KEY": bool(STRIPE_PUBLISHABLE_KEY),
        "ZAPIER_WEBHOOK_URL": bool(ZAPIER_WEBHOOK_URL),
        "SLACK_WEBHOOK_URL": bool(SLACK_WEBHOOK_URL),
        "ORCHESTRATOR_WEBHOOK_URL": bool(ORCHESTRATOR_WEBHOOK_URL),
        "SUPABASE_URL": bool(SUPABASE_URL),
        "SUPABASE_SERVICE_KEY": bool(SUPABASE_SERVICE_KEY),
        "OPENAI_API_KEY": bool(OPENAI_API_KEY),
        "ANTHROPIC_API_KEY": bool(ANTHROPIC_API_KEY),
        "LINEAR_API_KEY": bool(LINEAR_API_KEY),
        "GITHUB_TOKEN": bool(GITHUB_TOKEN),
        "APP_URL": bool(APP_URL),
    }

# ── ROOT ──────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "status": "MARS API LIVE",
        "version": "2.1.0",
        "org": "Garcar Enterprise OS",
        "endpoints": [
            "/health", "/revenue/dashboard", "/lead/capture",
            "/invoice/create", "/payment/link", "/deal/submit", "/deal/list",
            "/agent/run", "/webhook/stripe", "/notify"
        ],
        "keys_configured": sum(1 for v in key_status().values() if v),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
def health():
    keys = key_status()
    return {
        "status": "ok",
        "service": "mars-api",
        "version": "2.1.0",
        "stripe_ready": keys["STRIPE_SECRET_KEY"],
        "supabase_ready": keys["SUPABASE_URL"] and keys["SUPABASE_SERVICE_KEY"],
        "webhooks_ready": keys["ZAPIER_WEBHOOK_URL"] or keys["SLACK_WEBHOOK_URL"] or keys["ORCHESTRATOR_WEBHOOK_URL"],
        "keys": keys,
        "timestamp": datetime.utcnow().isoformat()
    }

# ── STRIPE WEBHOOK ────────────────────────────────────────────────────────────
@app.post("/webhook/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, STRIPE_WEBHOOK_SECRET or "")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    event_type = event["type"]
    data = event["data"]["object"]
    await fire_webhooks({
        "event": event_type,
        "data": str(data)[:500],
        "timestamp": datetime.utcnow().isoformat()
    })
    return {"received": True, "event": event_type}

# ── LEAD CAPTURE ──────────────────────────────────────────────────────────────
@app.post("/lead/capture")
async def capture_lead(request: Request):
    data = await request.json()
    required = ["name", "email"]
    for field in required:
        if field not in data:
            raise HTTPException(status_code=422, detail=f"Missing field: {field}")
    lead_id = f"lead_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    payload = {
        "event": "new_lead",
        "id": lead_id,
        "source": data.get("source", "mars-api"),
        "timestamp": datetime.utcnow().isoformat(),
        **data
    }
    # Persist to Supabase when available
    sb = get_supabase()
    if sb:
        try:
            sb.table("leads").insert({
                "id": lead_id,
                "name": data.get("name"),
                "email": data.get("email"),
                "source": payload["source"],
                "payload": data,
                "created_at": payload["timestamp"]
            }).execute()
        except Exception:
            pass
    await fire_webhooks(payload)
    return {"status": "lead captured", "id": lead_id, "data": data}

# ── REVENUE DASHBOARD ─────────────────────────────────────────────────────────
@app.get("/revenue/dashboard")
async def revenue_dashboard():
    revenue_data = await fetch_stripe_revenue()
    return {
        "status": "live",
        "org": "Garcar Enterprise OS",
        "revenue": revenue_data,
        "timestamp": datetime.utcnow().isoformat()
    }

async def fetch_stripe_revenue():
    if not STRIPE_SECRET_KEY:
        return {
            "available": 0, "pending": 0,
            "note": "Set STRIPE_SECRET_KEY (canonical Garcar key) to see live data"
        }
    try:
        balance = stripe.Balance.retrieve()
        available = sum(b["amount"] for b in balance["available"]) / 100
        pending = sum(b["amount"] for b in balance["pending"]) / 100
        charges = stripe.Charge.list(limit=10)
        recent = [{
            "id": c["id"],
            "amount": c["amount"] / 100,
            "currency": c["currency"],
            "status": c["status"],
            "created": datetime.fromtimestamp(c["created"]).isoformat()
        } for c in charges["data"]]
        return {
            "available": available,
            "pending": pending,
            "currency": "usd",
            "recent_charges": recent
        }
    except Exception as e:
        return {"available": 0, "pending": 0, "error": str(e)}

# ── INVOICE CREATE ────────────────────────────────────────────────────────────
@app.post("/invoice/create")
async def create_invoice(request: Request):
    data = await request.json()
    customer_email = data.get("email")
    amount_cents = int(data.get("amount", 0) * 100)
    description = data.get("description", "Garcar Enterprise Services")
    if not customer_email or amount_cents <= 0:
        raise HTTPException(status_code=422, detail="email and amount required")
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="STRIPE_SECRET_KEY not configured")
    try:
        customer = stripe.Customer.create(
            email=customer_email,
            name=data.get("name", "")
        )
        stripe.InvoiceItem.create(
            customer=customer["id"],
            amount=amount_cents,
            currency="usd",
            description=description
        )
        invoice = stripe.Invoice.create(customer=customer["id"], auto_advance=True)
        finalized = stripe.Invoice.finalize_invoice(invoice["id"])
        await fire_webhooks({
            "event": "invoice_created",
            "email": customer_email,
            "amount": amount_cents / 100,
            "invoice_id": finalized["id"],
            "invoice_url": finalized.get("hosted_invoice_url", "")
        })
        return {
            "status": "invoice created",
            "invoice_id": finalized["id"],
            "amount": amount_cents / 100,
            "invoice_url": finalized.get("hosted_invoice_url", ""),
            "pdf": finalized.get("invoice_pdf", "")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── PAYMENT LINK ──────────────────────────────────────────────────────────────
@app.post("/payment/link")
async def create_payment_link(request: Request):
    data = await request.json()
    amount_cents = int(data.get("amount", 0) * 100)
    name = data.get("name", "Garcar Enterprise Service")
    if amount_cents <= 0:
        raise HTTPException(status_code=422, detail="amount required")
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="STRIPE_SECRET_KEY not configured")
    try:
        price = stripe.Price.create(
            unit_amount=amount_cents,
            currency="usd",
            product_data={"name": name}
        )
        link = stripe.PaymentLink.create(line_items=[{"price": price["id"], "quantity": 1}])
        await fire_webhooks({
            "event": "payment_link_created",
            "name": name,
            "amount": amount_cents / 100,
            "url": link["url"]
        })
        return {
            "status": "payment link created",
            "url": link["url"],
            "amount": amount_cents / 100,
            "product": name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── DEAL DESK ─────────────────────────────────────────────────────────────────
@app.post("/deal/submit")
async def submit_deal(request: Request):
    data = await request.json()
    deal_id = f"deal_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    deal = {
        "event": "new_deal",
        "deal_id": deal_id,
        "company": data.get("company", ""),
        "contact": data.get("contact", ""),
        "email": data.get("email", ""),
        "value": data.get("value", 0),
        "service": data.get("service", ""),
        "notes": data.get("notes", ""),
        "status": "submitted",
        "timestamp": datetime.utcnow().isoformat()
    }
    sb = get_supabase()
    if sb:
        try:
            sb.table("deals").insert({
                "id": deal_id,
                "company": deal["company"],
                "contact": deal["contact"],
                "email": deal["email"],
                "value": deal["value"],
                "service": deal["service"],
                "notes": deal["notes"],
                "status": deal["status"],
                "created_at": deal["timestamp"]
            }).execute()
        except Exception:
            pass
    await fire_webhooks(deal)
    return {"status": "deal submitted", "deal_id": deal_id, "deal": deal}

@app.get("/deal/list")
def list_deals():
    sb = get_supabase()
    if sb:
        try:
            result = sb.table("deals").select("*").order("created_at", desc=True).limit(50).execute()
            return {
                "status": "ok",
                "deals": result.data or [],
                "source": "supabase",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "ok",
                "message": f"Supabase query failed: {e}",
                "deals": [],
                "timestamp": datetime.utcnow().isoformat()
            }
    return {
        "status": "ok",
        "message": "Set SUPABASE_URL + SUPABASE_SERVICE_KEY for live deal pipeline",
        "deals": [],
        "timestamp": datetime.utcnow().isoformat()
    }

# ── AGENT ORCHESTRATION ───────────────────────────────────────────────────────
@app.post("/agent/run")
async def run_agent(request: Request):
    data = await request.json()
    task = data.get("task", "")
    agent = data.get("agent", "MARS")
    priority = data.get("priority", "normal")
    run_id = f"run_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    await fire_webhooks({
        "event": "agent_task",
        "agent": agent,
        "task": task,
        "priority": priority,
        "run_id": run_id
    })
    return {
        "agent": agent,
        "status": "queued",
        "run_id": run_id,
        "task": task,
        "priority": priority,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/agent/status/{run_id}")
def agent_status(run_id: str):
    return {
        "run_id": run_id,
        "status": "running",
        "message": "Connect task queue / Linear for live status",
        "timestamp": datetime.utcnow().isoformat()
    }

# ── OUTREACH / NOTIFICATION ───────────────────────────────────────────────────
@app.post("/notify")
async def send_notification(request: Request):
    data = await request.json()
    payload = {
        "event": "notification",
        "channel": data.get("channel", "email"),
        "subject": data.get("subject", ""),
        "message": data.get("message", ""),
        "to": data.get("to", ""),
        "timestamp": datetime.utcnow().isoformat()
    }
    await fire_webhooks(payload)
    return {"status": "notification queued", "payload": payload}

# ── UTILITY — multi-webhook fan-out (Zapier + Slack + Orchestrator) ───────────
async def fire_webhooks(payload: dict):
    urls = [u for u in (ZAPIER_WEBHOOK_URL, SLACK_WEBHOOK_URL, ORCHESTRATOR_WEBHOOK_URL) if u]
    if not urls:
        return
    async with httpx.AsyncClient() as client:
        for url in urls:
            try:
                # Slack expects a slightly different shape; send raw for Zapier/Orchestrator
                body = payload
                if "hooks.slack.com" in url:
                    text = f"*{payload.get('event', 'mars')}*\n```{str(payload)[:800]}```"
                    body = {"text": text}
                await client.post(url, json=body, timeout=5)
            except Exception:
                pass
