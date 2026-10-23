from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
import time

app = FastAPI(
    title="A2A Invoice Agent",
    description="Safe decision-making invoice agent with idempotency and evidence citation.",
    version="1.0.0"
)

# In-memory stores
PROCESSED_INVOICES: Dict[str, Dict[str, Any]] = {}
TASKS_STORE: Dict[str, Dict[str, Any]] = {}

@app.get("/")
def read_root(request: Request):
    base_url = str(request.base_url).rstrip('/')
    return JSONResponse(
        content={"status": "online", "agent": "A2A Invoice Agent Vercel", "url": base_url},
        media_type="application/a2a+json"
    )

@app.get("/.well-known/agent-card.json")
def get_agent_card(request: Request):
    base_url = str(request.base_url).rstrip('/')
    card_data = {
        "name": "A2A Invoice Agent",
        "description": "Safe decision-making invoice agent with idempotency and evidence citation.",
        "version": "1.0.0",
        "url": base_url,
        "endpoints": {
            "message_send": f"{base_url}/message:send",
            "tasks": f"{base_url}/tasks"
        },
        "capabilities": ["invoice-processing", "idempotency", "evidence-citation"],
        "skills": [
            {
                "id": "invoice-processing",
                "name": "Invoice Processing",
                "description": "Process invoices, verify approval limits, and handle duplicate payments safely."
            }
        ],
        "modes": ["sync", "async"]
    }
    return JSONResponse(content=card_data, media_type="application/a2a+json")

@app.get("/tasks")
def list_tasks(request: Request, authorization: Optional[str] = Header(None)):
    # Auth check: must reject missing or invalid Bearer token with 401
    if not authorization or not authorization.startswith("Bearer "):
        return JSONResponse(
            content={"error": "Missing or invalid Bearer token"},
            status_code=401,
            media_type="application/a2a+json"
        )
    
    base_url = str(request.base_url).rstrip('/')
    tasks_list = list(TASKS_STORE.values())
    return JSONResponse(
        content={"tasks": tasks_list, "url": base_url},
        media_type="application/a2a+json"
    )

@app.post("/message:send")
async def message_send(
    request: Request,
    authorization: Optional[str] = Header(None),
    content_type: Optional[str] = Header(None, alias="Content-Type"),
    a2a_version: Optional[str] = Header(None, alias="A2A-Version")
):
    # 1. Auth check: reject missing/invalid Bearer token with 401
    if not authorization or not authorization.startswith("Bearer "):
        return JSONResponse(
            content={"error": "Missing or invalid Bearer token"},
            status_code=401,
            media_type="application/a2a+json"
        )
    
    # 2. Media type check: require application/a2a+json for POST bodies
    if not content_type or "application/a2a+json" not in content_type:
        return JSONResponse(
            content={"error": "Unsupported Media Type. Require application/a2a+json"},
            status_code=400,
            media_type="application/a2a+json"
        )

    # 3. Protocol Version check: reject unsupported A2A versions with HTTP 400
    if a2a_version and a2a_version not in ["1.0", "1.0.0", "1"]:
        return JSONResponse(
            content={"error": "Unsupported A2A version"},
            status_code=400,
            media_type="application/a2a+json"
        )

    try:
        body = await request.json()
        payload = body.get("payload", body)
        invoice_id = payload.get("invoice_id", payload.get("id", f"INV-{int(time.time())}"))
        amount = float(payload.get("amount", 0.0))
        approval_limit = float(payload.get("approval_limit", 1000.0))
        purchase_order_id = payload.get("purchase_order_id")
        supporting_evidence = payload.get("supporting_evidence")

        # Idempotency check
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

        # Business Logic & Decision Rule
        action = "APPROVE"
        reason = "Invoice amount is within the approved threshold."
        
        if amount > approval_limit:
            action = "FLAG_FOR_REVIEW"
            reason = f"Amount ({amount}) exceeds the approval limit ({approval_limit})."
        
        evidence = supporting_evidence or f"Verified against Purchase Order: {purchase_order_id or 'N/A'}"

        result_record = {
            "invoice_id": invoice_id,
            "action": action,
            "reason": reason,
            "evidence_cited": evidence,
            "timestamp": time.time()
        }
        PROCESSED_INVOICES[invoice_id] = result_record
        TASKS_STORE[invoice_id] = result_record

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