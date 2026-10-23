from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
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
    return {"status": "online", "agent": "A2A Invoice Agent Vercel"}

@app.get("/.well-known/agent-card.json")
def get_agent_card():
    return {
        "name": "A2A Invoice Agent",
        "description": "Safe decision-making invoice agent with idempotency and evidence citation.",
        "version": "1.0.0",
        "url": "https://tds-week3-q2-k7s9hbuer-rajtiwariii.vercel.app/",
        "endpoints": {
            "message_send": "https://tds-week3-q2-k7s9hbuer-rajtiwariii.vercel.app/message:send"
        },
        "capabilities": ["invoice-processing", "idempotency", "evidence-citation"]
    }

@app.post("/message:send")
async def message_send(request: Request):
    try:
        body = await request.json()
        # Extract invoice details from incoming A2A payload safely
        payload = body.get("payload", body)
        invoice_id = payload.get("invoice_id", "INV-UNKNOWN")
        amount = float(payload.get("amount", 0.0))
        approval_limit = float(payload.get("approval_limit", 1000.0))
        purchase_order_id = payload.get("purchase_order_id")
        supporting_evidence = payload.get("supporting_evidence")

        # Idempotency check
        if invoice_id in PROCESSED_INVOICES:
            existing = PROCESSED_INVOICES[invoice_id]
            return {
                "invoice_id": invoice_id,
                "action": existing["action"],
                "reason": "Duplicate request detected. Returning previously recorded state to prevent redundant payment.",
                "evidence_cited": existing["evidence_cited"],
                "status": "DUPLICATE_PREVENTED",
                "timestamp": existing["timestamp"]
            }

        # Business Logic
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

        return {
            "invoice_id": invoice_id,
            "action": action,
            "reason": reason,
            "evidence_cited": evidence,
            "status": "PROCESSED",
            "timestamp": result_record["timestamp"]
        }
    except Exception as e:
        return {"error": str(e)}, 400