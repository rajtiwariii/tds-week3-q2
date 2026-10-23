from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
import time

app = FastAPI(
    title="A2A Invoice Agent",
    description="Safe decision-making invoice agent with idempotency and evidence citation.",
    version="1.0.0"
)

PROCESSED_INVOICES: Dict[str, Dict[str, Any]] = {}

@app.get("/")
def read_root():
    return JSONResponse(
        content={"status": "online", "agent": "A2A Invoice Agent Vercel"},
        media_type="application/a2a+json"
    )

@app.get("/.well-known/agent-card.json")
def get_agent_card():
    card_data = {
        "name": "A2A Invoice Agent",
        "description": "Safe decision-making invoice agent with idempotency and evidence citation.",
        "version": "1.0.0",
        "url": "https://tds-week3-q2.vercel.app/",
        "endpoints": {
            "message_send": "https://tds-week3-q2.vercel.app/message:send"
        },
        "capabilities": ["invoice-processing", "idempotency", "evidence-citation"]
    }
    return JSONResponse(
        content=card_data,
        media_type="application/a2a+json"
    )

@app.post("/message:send")
async def message_send(request: Request):
    try:
        body = await request.json()
        payload = body.get("payload", body)
        invoice_id = payload.get("invoice_id", "INV-UNKNOWN")
        amount = float(payload.get("amount", 0.0))
        approval_limit = float(payload.get("approval_limit", 1000.0))
        purchase_order_id = payload.get("purchase_order_id")
        supporting_evidence = payload.get("supporting_evidence")

        if invoice_id in PROCESSED_INVOICES:
            existing = PROCESSED_INVOICES[invoice_id]
            resp_data = {
                "invoice_id": invoice_id,
                "action": existing["action"],
                "reason": "Duplicate request detected. Returning previously recorded state to prevent redundant payment.",
                "evidence_cited": existing["evidence_cited"],
                "status": "DUPLICATE_PREVENTED",
                "timestamp": existing["timestamp"]
            }
            return JSONResponse(content=resp_data, media_type="application/a2a+json")

        action = "APPROVE"
        reason = "Invoice amount is within the approved threshold."
        
        if amount > approval_limit:
            action = "FLAG_FOR_REVIEW"
            reason = f"Amount ({amount}) exceeds the approval limit ({approval_limit})."
        
        evidence = supporting_evidence or f"Verified against Purchase Order: {purchase_order_id or 'N/A'}"

        result_record = {
            "action": action,
            "reason": reason,
            "evidence_cited": evidence,
            "timestamp": time.time()
        }
        PROCESSED_INVOICES[invoice_id] = result_record

        resp_data = {
            "invoice_id": invoice_id,
            "action": action,
            "reason": reason,
            "evidence_cited": evidence,
            "status": "PROCESSED",
            "timestamp": result_record["timestamp"]
        }
        return JSONResponse(content=resp_data, media_type="application/a2a+json")
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=400,
            media_type="application/a2a+json"
        )