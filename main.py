from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import stripe, os, httpx
from datetime import datetime

app = FastAPI(title="MARS API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

@app.get("/")
def root():
    return {"status": "MARS API LIVE", "org": "Garcar Enterprise OS",
            "timestamp": datetime.utcnow().isoformat()}

@app.get("/health")
def health():
    return {"status": "ok", "service": "mars-api"}

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
    await fire_zapier({"event": event_type, "data": str(data)[:200]})
    return {"received": True, "event": event_type}

@app.post("/lead/capture")
async def capture_lead(request: Request):
    data = await request.json()
    await fire_zapier({"event": "new_lead", **data})
    return {"status": "lead captured", "data": data}

@app.get("/revenue/dashboard")
def revenue_dashboard():
    return {"status": "MARS API LIVE", "total_revenue": 0,
            "message": "Connect Supabase to see live data",
            "timestamp": datetime.utcnow().isoformat()}

@app.post("/agent/run")
async def run_agent(request: Request):
    data = await request.json()
    task = data.get("task", "")
    return {"agent": "MARS", "status": "received", "task": task,
            "timestamp": datetime.utcnow().isoformat()}

async def fire_zapier(payload: dict):
    url = os.getenv("ZAPIER_WEBHOOK_URL", "")
    if url:
        async with httpx.AsyncClient() as client:
            try:
                await client.post(url, json=payload, timeout=5)
            except Exception:
                pass
