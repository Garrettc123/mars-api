from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import stripe, os, httpx
from datetime import datetime
from typing import Optional

app = FastAPI(title="MARS API", version="2.0.0", description="Garcar Enterprise Revenue System")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

# ── ROOT ──────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "status": "MARS API LIVE",
        "version": "2.0.0",
        "org": "Garcar Enterprise OS",
        "endpoints": ["/health", "/revenue/dashboard", "/lead/capture",
                      "/invoice/create", "/payment/link", "/deal/submit",
                      "/agent/run", "/webhook/stripe"],
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
def health():
    return {"status": "ok", "service": "mars-api", "version": "2.0.0"}

# ── STRIPE WEBHOOK ────────────────────────────────────────────────────────────
@app.post("/webhook/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, os.getenv("STRIPE_WEBHOOK_SECRET", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    event_type = event["type"]
    data = event["data"]["object"]
    await fire_zapier({"event": event_type, "data": str(data)[:500],
                       "timestamp": datetime.utcnow().isoformat()})
    return {"received": True, "event": event_type}

# ── LEAD CAPTURE ──────────────────────────────────────────────────────────────
@app.post("/lead/capture")
async def capture_lead(request: Request):
    data = await request.json()
    required = ["name", "email"]
    for field in required:
        if field not in data:
            raise HTTPException(status_code=422, detail=f"Missing field: {field}")
    payload = {
        "event": "new_lead",
        "source": data.get("source", "mars-api"),
        "timestamp": datetime.utcnow().isoformat(),
        **data
    }
    await fire_zapier(payload)
    return {"status": "lead captured", "id": f"lead_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}", "data": data}

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
    try:
        balance = stripe.Balance.retrieve()
        available = sum(b["amount"] for b in balance["available"]) / 100
        pending = sum(b["amount"] for b in balance["pending"]) / 100
        charges = stripe.Charge.list(limit=10)
        recent = [{"id": c["id"], "amount": c["amount"] / 100,
                   "currency": c["currency"], "status": c["status"],
                   "created": datetime.fromtimestamp(c["created"]).isoformat()}
                  for c in charges["data"]]
        return {"available": available, "pending": pending,
                "currency": "usd", "recent_charges": recent}
    except Exception as e:
        return {"available": 0, "pending": 0, "error": str(e),
                "note": "Set STRIPE_SECRET_KEY to see live data"}

# ── INVOICE CREATE ────────────────────────────────────────────────────────────
@app.post("/invoice/create")
async def create_invoice(request: Request):
    data = await request.json()
    customer_email = data.get("email")
    amount_cents = int(data.get("amount", 0) * 100)
    description = data.get("description", "Garcar Enterprise Services")
    if not customer_email or amount_cents <= 0:
        raise HTTPException(status_code=422, detail="email and amount required")
    try:
        customer = stripe.Customer.create(email=customer_email,
                                          name=data.get("name", ""))
        invoice_item = stripe.InvoiceItem.create(
            customer=customer["id"],
            amount=amount_cents,
            currency="usd",
            description=description
        )
        invoice = stripe.Invoice.create(customer=customer["id"],
                                        auto_advance=True)
        finalized = stripe.Invoice.finalize_invoice(invoice["id"])
        await fire_zapier({"event": "invoice_created", "email": customer_email,
                           "amount": amount_cents / 100, "invoice_id": finalized["id"],
                           "invoice_url": finalized.get("hosted_invoice_url", "")})
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
    try:
        price = stripe.Price.create(
            unit_amount=amount_cents,
            currency="usd",
            product_data={"name": name}
        )
        link = stripe.PaymentLink.create(line_items=[{"price": price["id"], "quantity": 1}])
        await fire_zapier({"event": "payment_link_created", "name": name,
                           "amount": amount_cents / 100, "url": link["url"]})
        return {"status": "payment link created", "url": link["url"],
                "amount": amount_cents / 100, "product": name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── DEAL DESK ─────────────────────────────────────────────────────────────────
@app.post("/deal/submit")
async def submit_deal(request: Request):
    data = await request.json()
    deal = {
        "event": "new_deal",
        "deal_id": f"deal_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "company": data.get("company", ""),
        "contact": data.get("contact", ""),
        "email": data.get("email", ""),
        "value": data.get("value", 0),
        "service": data.get("service", ""),
        "notes": data.get("notes", ""),
        "status": "submitted",
        "timestamp": datetime.utcnow().isoformat()
    }
    await fire_zapier(deal)
    return {"status": "deal submitted", "deal_id": deal["deal_id"], "deal": deal}

@app.get("/deal/list")
def list_deals():
    return {"status": "ok", "message": "Connect Supabase for live deal pipeline",
            "deals": [], "timestamp": datetime.utcnow().isoformat()}

# ── AGENT ORCHESTRATION ───────────────────────────────────────────────────────
@app.post("/agent/run")
async def run_agent(request: Request):
    data = await request.json()
    task = data.get("task", "")
    agent = data.get("agent", "MARS")
    priority = data.get("priority", "normal")
    run_id = f"run_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    await fire_zapier({"event": "agent_task", "agent": agent,
                       "task": task, "priority": priority, "run_id": run_id})
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
    return {"run_id": run_id, "status": "running",
            "message": "Connect task queue for live status",
            "timestamp": datetime.utcnow().isoformat()}

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
    await fire_zapier(payload)
    return {"status": "notification queued", "payload": payload}

# ── UTILITY ───────────────────────────────────────────────────────────────────
async def fire_zapier(payload: dict):
    url = os.getenv("ZAPIER_WEBHOOK_URL", "")
    if url:
        async with httpx.AsyncClient() as client:
            try:
                await client.post(url, json=payload, timeout=5)
            except Exception:
                pass

from datetime import datetime as dt
