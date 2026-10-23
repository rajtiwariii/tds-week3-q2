from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import time

app = FastAPI(
    title="A2A Invoice Agent",
    description="Safe decision-making invoice agent with idempotency and evidence citation.",
    version="1.0.0"
)

# In-memory store for tracking processed invoices (idempotency state)
PROCESSED_INVOICES: Dict[str, Dict[str, Any]] = {}

class InvoiceRequest(BaseModel):
    invoice_id: str
    vendor: str
    amount: float
    currency: str = "USD"
    purchase_order_id: Optional[str] = None
    approval_limit: float = 1000.0
    supporting_evidence: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}

class InvoiceResponse(BaseModel):
    invoice_id: str
    action: str  # "APPROVE", "REJECT", "FLAG_FOR_REVIEW", "PAY"
    reason: str
    evidence_cited: str
    status: str  # "PROCESSED", "DUPLICATE_PREVENTED"
    timestamp: float

@app.get("/")
def read_root():
    return {"status": "online", "agent": "A2A Invoice Agent Vercel"}

@app.get("/.well-known/agent-card.json")
def get_agent_card():
    return {
        "name": "A2A Invoice Agent",
        "description": "Safe decision-making invoice agent with idempotency and evidence citation.",
        "version": "1.0.0",
        "url": "https://tds-week3-q2.vercel.app/",
        "endpoints": {
            "process_invoice": "https://tds-week3-q2.vercel.app/process-invoice"
        },
        "capabilities": ["invoice-processing", "idempotency", "evidence-citation"]
    }

@app.post("/process-invoice", response_model=InvoiceResponse)
async def process_invoice(payload: InvoiceRequest):
    invoice_id = payload.invoice_id

    # 1. Check Idempotency / Duplicate State
    if invoice_id in PROCESSED_INVOICES:
        existing = PROCESSED_INVOICES[invoice_id]
        return InvoiceResponse(
            invoice_id=invoice_id,
            action=existing["action"],
            reason="Duplicate request detected. Returning previously recorded state to prevent redundant payment.",
            evidence_cited=existing["evidence_cited"],
            status="DUPLICATE_PREVENTED",
            timestamp=existing["timestamp"]
        )

    # 2. Business Logic & Decision Rule Evaluation
    action = "APPROVE"
    reason = "Invoice amount is within the approved threshold."
    
    if payload.amount > payload.approval_limit:
        action = "FLAG_FOR_REVIEW"
        reason = f"Amount ({payload.amount}) exceeds the approval limit ({payload.approval_limit})."
    
    evidence = payload.supporting_evidence or f"Verified against Purchase Order: {payload.purchase_order_id or 'N/A'}"

    # 3. Save State
    result_record = {
        "action": action,
        "reason": reason,
        "evidence_cited": evidence,
        "timestamp": time.time()
    }
    PROCESSED_INVOICES[invoice_id] = result_record

    return InvoiceResponse(
        invoice_id=invoice_id,
        action=action,
        reason=reason,
        evidence_cited=evidence,
        status="PROCESSED",
        timestamp=result_record["timestamp"]
    )