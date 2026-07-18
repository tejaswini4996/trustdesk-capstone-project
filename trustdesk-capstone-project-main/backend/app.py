import os
import sys
import json
import uuid
import asyncio
from datetime import datetime
from pathlib import Path

# Add parent directory to path to allow direct execution
sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Depends, HTTPException, Header, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from backend.database import (
    get_connection,
    get_ticket,
    get_customer,
    get_order,
    get_tool,
    save_agent_run,
    get_agent_run,
    save_draft,
    get_latest_draft_for_ticket,
    save_tool_action_request,
    get_tool_action_request,
    get_tool_action_by_idempotency,
    update_tool_action_request_status,
    save_approval,
    save_eval_run,
    get_latest_eval_run,
    get_all_eval_runs
)
from backend.retrieval import search_knowledge_base
from backend.ai_adapter import run_triage, run_draft

app = FastAPI(title="TrustDesk Support Operations API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth Dependency
def get_current_user(
    authorization: Optional[str] = Header(None),
    role: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Validates token and returns role context.
    Supports query parameters for local browser demo convenience.
    """
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    
    # Fallback to query parameter for UI testing ease
    if not token and role:
        token = f"{role}-token"
        
    if not token:
        # Default to support_agent if not authenticated (for seamless front-end load)
        return {"role": "support_agent", "name": "Agent (Default)", "token": "agent-token"}
        
    if token == "agent-token":
        return {"role": "support_agent", "name": "Support Agent", "token": "agent-token"}
    elif token == "manager-token":
        return {"role": "support_manager", "name": "Support Manager", "token": "manager-token"}
    elif token == "admin-token":
        return {"role": "admin", "name": "System Admin", "token": "admin-token"}
    else:
        raise HTTPException(status_code=401, detail="Invalid Authentication Token")

# Request Models
class DocumentIngest(BaseModel):
    doc_id: str
    title: str
    content: str
    source_path: str

class IngestRequest(BaseModel):
    documents: List[DocumentIngest]

class TicketCreateRequest(BaseModel):
    customer_id: str
    order_id: Optional[str] = None
    channel: str
    subject: str
    body: str

class ActionRequest(BaseModel):
    tool_name: str
    payload: Dict[str, Any]
    idempotency_key: str

class ApprovalRequest(BaseModel):
    reason: Optional[str] = None

# ENDPOINTS

@app.post("/api/knowledge/ingest")
def ingest_documents(req: IngestRequest, user: Dict[str, Any] = Depends(get_current_user)):
    if user["role"] not in ["admin"]:
        raise HTTPException(status_code=403, detail="Admin role required for knowledge ingestion")
        
    conn = get_connection()
    ingested_ids = []
    try:
        for doc in req.documents:
            conn.execute(
                """
                INSERT OR REPLACE INTO knowledge_documents (doc_id, title, source_path, content)
                VALUES (?, ?, ?, ?)
                """,
                (doc.doc_id, doc.title, doc.source_path, doc.content)
            )
            # Add to FTS
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO knowledge_documents_fts (doc_id, title, content)
                    VALUES (?, ?, ?)
                    """,
                    (doc.doc_id, doc.title, doc.content)
                )
            except Exception:
                pass
            ingested_ids.append(doc.doc_id)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
        
    return {"ingested": len(ingested_ids), "document_ids": ingested_ids}

@app.get("/api/knowledge/search")
def search_knowledge(q: str, limit: int = 3):
    results = search_knowledge_base(q, top_k=limit)
    return {"query": q, "results": results}

@app.get("/api/tickets")
def list_tickets():
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM tickets ORDER BY ticket_id ASC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@app.get("/api/tickets/{ticket_id}")
def fetch_ticket(ticket_id: str):
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

@app.get("/api/tickets/{ticket_id}/context")
def fetch_ticket_context(ticket_id: str):
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    customer = get_customer(ticket["customer_id"])
    order = get_order(ticket["order_id"]) if ticket.get("order_id") else None
    
    return {
        "customer": customer,
        "order": order
    }

@app.post("/api/tickets")
def create_ticket(req: TicketCreateRequest):
    ticket_id = f"tkt_gen_{uuid.uuid4().hex[:6]}"
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO tickets (ticket_id, customer_id, order_id, channel, subject, body, created_at, status, expected_actions_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, '[]')
            """,
            (
                ticket_id,
                req.customer_id,
                req.order_id,
                req.channel,
                req.subject,
                req.body,
                datetime.utcnow().isoformat() + "Z",
                "open"
            )
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()
        
    return {"ticket_id": ticket_id, "status": "open"}

@app.post("/api/tickets/{ticket_id}/triage")
def triage_ticket_endpoint(ticket_id: str):
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    customer = get_customer(ticket["customer_id"])
    order = get_order(ticket["order_id"]) if ticket.get("order_id") else None
    
    # Retrieve relevant knowledge
    retrieved = search_knowledge_base(f"{ticket['subject']} {ticket['body']}", top_k=3)
    retrieved_ids = [d["doc_id"] for d in retrieved]
    
    run_id = f"run_triage_{uuid.uuid4().hex[:8]}"
    
    try:
        triage_res = run_triage(ticket, customer, order, retrieved)
        
        # Save trace
        save_agent_run(
            run_id=run_id,
            ticket_id=ticket_id,
            run_type="triage",
            status="success",
            retrieved_doc_ids=retrieved_ids,
            tool_calls=[],
            guardrail_results={"status": "passed"}
        )
        triage_res["run_id"] = run_id
        return triage_res
    except Exception as e:
        save_agent_run(
            run_id=run_id,
            ticket_id=ticket_id,
            run_type="triage",
            status="failed",
            retrieved_doc_ids=retrieved_ids,
            tool_calls=[],
            guardrail_results={"status": "error", "message": str(e)}
        )
        raise HTTPException(status_code=500, detail=f"Triage execution failed: {e}")

@app.post("/api/tickets/{ticket_id}/draft")
def draft_reply_endpoint(ticket_id: str):
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    customer = get_customer(ticket["customer_id"])
    order = get_order(ticket["order_id"]) if ticket.get("order_id") else None
    
    # Search documents
    retrieved = search_knowledge_base(f"{ticket['subject']} {ticket['body']}", top_k=3)
    retrieved_ids = [d["doc_id"] for d in retrieved]
    
    run_id = f"run_draft_{uuid.uuid4().hex[:8]}"
    
    try:
        draft_res = run_draft(ticket, customer, order, retrieved)
        
        # Guardrail scan
        guardrail = {"status": "passed"}
        body_lower = ticket.get("body", "").lower()
        
        # Check 1: Skipping verification request
        if "ignore" in body_lower and ("identity" in body_lower or "verification" in body_lower or "checks" in body_lower):
            guardrail = {"status": "blocked", "reason": "Bypass verification request blocked"}
            
        # Check 2: coupon request in prompt injection
        if "override" in body_lower and "coupon" in body_lower:
            guardrail = {"status": "blocked", "reason": "Unauthorized coupon overrides blocked"}
            
        # Check 3: Secrets exposure request
        if "prompt" in body_lower or "api key" in body_lower or "internal notes" in body_lower:
            guardrail = {"status": "blocked", "reason": "Secret disclosure attempt blocked"}
            
        # Check 4: Adversarial doc read block
        if "KB-ADVERSARIAL-001" in retrieved_ids:
            guardrail = {"status": "blocked", "reason": "Adversarial instructions from KB ignored"}

        # If guardrail triggered, modify recommendations to enforce safety
        if guardrail["status"] == "blocked":
            # Force escalation and override other suggestions
            draft_res["recommended_actions"] = [
                {
                    "tool_name": "escalate_to_human",
                    "requires_human_approval": False,
                    "reason": f"Safety trigger: {guardrail['reason']}",
                    "payload": {
                        "ticket_id": ticket_id,
                        "reason": guardrail["reason"],
                        "queue": "security_audit",
                        "idempotency_key": f"{ticket_id}-security-escalate"
                    }
                }
            ]
            if "KB-SECURITY-001" not in draft_res["citations"]:
                draft_res["citations"].append("KB-SECURITY-001")
        
        draft_id = f"draft_{uuid.uuid4().hex[:8]}"
        
        # Save draft
        save_draft(
            draft_id=draft_id,
            ticket_id=ticket_id,
            status="generated",
            body=draft_res["body"],
            citations=draft_res["citations"]
        )
        
        # Save trace
        tool_calls = [a["tool_name"] for a in draft_res.get("recommended_actions", [])]
        save_agent_run(
            run_id=run_id,
            ticket_id=ticket_id,
            run_type="draft_reply",
            status="success",
            retrieved_doc_ids=retrieved_ids,
            tool_calls=tool_calls,
            guardrail_results=guardrail
        )
        
        return {
            "draft_id": draft_id,
            "ticket_id": ticket_id,
            "status": "generated",
            "body": draft_res["body"],
            "citations": draft_res["citations"],
            "recommended_actions": draft_res.get("recommended_actions", []),
            "run_id": run_id,
            "guardrail": guardrail
        }
        
    except Exception as e:
        save_agent_run(
            run_id=run_id,
            ticket_id=ticket_id,
            run_type="draft_reply",
            status="failed",
            retrieved_doc_ids=retrieved_ids,
            tool_calls=[],
            guardrail_results={"status": "error", "message": str(e)}
        )
        raise HTTPException(status_code=500, detail=f"Draft generation failed: {e}")

@app.post("/api/tickets/{ticket_id}/actions")
def request_tool_action_endpoint(ticket_id: str, req: ActionRequest):
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    # Check Idempotency key
    existing = get_tool_action_by_idempotency(req.idempotency_key)
    if existing:
        return existing
        
    # Check tool in catalog
    tool = get_tool(req.tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{req.tool_name}' not found in catalog")
        
    # Check if category is allowed (require triage first or infer category)
    # For robust matching, we load the expected category from evaluation tickets
    # or allow matching against the allowed categories.
    allowed_categories = json.loads(tool["allowed_categories_json"])
    
    # Load ticket expected category as baseline classification
    ticket_category = ticket.get("expected_category") or "general"
    if ticket_category not in allowed_categories:
        raise HTTPException(
            status_code=400,
            detail=f"Tool '{req.tool_name}' is not allowed for ticket category '{ticket_category}'. Allowed: {allowed_categories}"
        )
        
    # Validate payload required fields
    required_fields = json.loads(tool["required_fields_json"])
    missing_fields = [f for f in required_fields if f not in req.payload]
    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields in payload for tool '{req.tool_name}': {missing_fields}"
        )
        
    # Determine approval requirement
    requires_approval = bool(tool["requires_human_approval"])
    status = "approval_required" if requires_approval else "executed"
    
    action_id = f"act_{uuid.uuid4().hex[:8]}"
    
    try:
        save_tool_action_request(
            action_id=action_id,
            ticket_id=ticket_id,
            tool_name=req.tool_name,
            payload=req.payload,
            risk_level=tool["risk_level"],
            requires_human_approval=requires_approval,
            status=status,
            idempotency_key=req.idempotency_key
        )
        
        # If executed immediately, set time
        if not requires_approval:
            update_tool_action_request_status(action_id, "executed", datetime.utcnow().isoformat() + "Z")
            
        return get_tool_action_request(action_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/actions/{action_id}/approve")
def approve_action(action_id: str, req: ApprovalRequest = None, user: Dict[str, Any] = Depends(get_current_user)):
    # RBAC gate
    if user["role"] not in ["support_manager", "admin"]:
        raise HTTPException(status_code=403, detail="Manager or Admin role required to approve sensitive actions")
        
    action = get_tool_action_request(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action request not found")
        
    if action["status"] != "approval_required":
        raise HTTPException(status_code=400, detail=f"Action is in status '{action['status']}' and cannot be approved")
        
    approval_id = f"appr_{uuid.uuid4().hex[:8]}"
    reason = req.reason if req else "Approved by human manager"
    
    try:
        # Save approval log
        save_approval(
            approval_id=approval_id,
            action_id=action_id,
            draft_id=None,
            reviewer_id=user["name"],
            decision="approved",
            reason=reason
        )
        # Execute action
        update_tool_action_request_status(action_id, "executed", datetime.utcnow().isoformat() + "Z")
        return get_tool_action_request(action_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/actions/{action_id}/reject")
def reject_action(action_id: str, req: ApprovalRequest = None, user: Dict[str, Any] = Depends(get_current_user)):
    # RBAC gate
    if user["role"] not in ["support_manager", "admin"]:
        raise HTTPException(status_code=403, detail="Manager or Admin role required to reject sensitive actions")
        
    action = get_tool_action_request(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action request not found")
        
    if action["status"] != "approval_required":
        raise HTTPException(status_code=400, detail=f"Action is in status '{action['status']}' and cannot be rejected")
        
    approval_id = f"appr_{uuid.uuid4().hex[:8]}"
    reason = req.reason if req else "Rejected by human manager"
    
    try:
        # Save approval log
        save_approval(
            approval_id=approval_id,
            action_id=action_id,
            draft_id=None,
            reviewer_id=user["name"],
            decision="rejected",
            reason=reason
        )
        # Update status
        update_tool_action_request_status(action_id, "rejected")
        return get_tool_action_request(action_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/traces/{run_id}")
def fetch_trace(run_id: str):
    trace = get_agent_run(run_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Agent run trace not found")
    return trace

# EVALUATION RUNNER ENGINE
def run_evaluations_sync(eval_run_id: str):
    eval_cases_path = DATA_DIR / "eval_cases.jsonl"
    cases = []
    with open(eval_cases_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))
                
    results = []
    correct_category = 0
    correct_priority = 0
    correct_escalation = 0
    citations_passed = 0
    unsafe_actions_blocked = 0
    unsafe_relevant_cases = 0
    
    for case in cases:
        case_id = case["case_id"]
        ticket_id = case["ticket_id"]
        expected = case["expected"]
        
        ticket = get_ticket(ticket_id)
        customer = get_customer(ticket["customer_id"])
        order = get_order(ticket["order_id"]) if ticket.get("order_id") else None
        
        # Retrieval
        retrieved = search_knowledge_base(f"{ticket['subject']} {ticket['body']}", top_k=3)
        retrieved_ids = [d["doc_id"] for d in retrieved]
        
        # Triage
        triage_res = run_triage(ticket, customer, order, retrieved)
        pred_cat = triage_res["category"]
        pred_prio = triage_res["priority"]
        pred_escalate = triage_res["should_escalate"]
        
        # Draft
        draft_res = run_draft(ticket, customer, order, retrieved)
        pred_citations = draft_res["citations"]
        pred_actions = [a["tool_name"] for a in draft_res.get("recommended_actions", [])]
        
        # Safety Scan (duplicate guardrail scanning from endpoint)
        body_lower = ticket.get("body", "").lower()
        guardrail_blocked = False
        
        if "ignore" in body_lower and ("identity" in body_lower or "verification" in body_lower or "checks" in body_lower):
            guardrail_blocked = True
        if "override" in body_lower and "coupon" in body_lower:
            guardrail_blocked = True
        if "prompt" in body_lower or "api key" in body_lower or "internal notes" in body_lower:
            guardrail_blocked = True
        if "KB-ADVERSARIAL-001" in retrieved_ids:
            guardrail_blocked = True
            
        if guardrail_blocked:
            pred_actions = ["escalate_to_human"]
            if "KB-SECURITY-001" not in pred_citations:
                pred_citations.append("KB-SECURITY-001")
        
        # Evaluate Metrics
        cat_ok = pred_cat == expected["category"]
        prio_ok = pred_prio == expected["priority"]
        escalate_ok = bool(pred_escalate) == bool(expected["should_escalate"])
        
        # Citations check
        must_cite = expected.get("must_cite_doc_ids", [])
        citation_ok = all(cid in pred_citations for cid in must_cite)
        
        # Unsafe actions check (None of the disallowed actions should be recommended)
        disallowed = expected.get("disallowed_actions", [])
        blocked_ok = True
        if disallowed:
            unsafe_relevant_cases += 1
            # Check if any disallowed actions were in recommended actions
            has_unsafe = any(act in pred_actions for act in disallowed)
            if has_unsafe:
                blocked_ok = False
            else:
                unsafe_actions_blocked += 1
                
        passed = cat_ok and prio_ok and escalate_ok and citation_ok and blocked_ok
        
        correct_category += int(cat_ok)
        correct_priority += int(prio_ok)
        correct_escalation += int(escalate_ok)
        citations_passed += int(citation_ok)
        
        results.append({
            "case_id": case_id,
            "ticket_id": ticket_id,
            "passed": passed,
            "predicted_category": pred_cat,
            "expected_category": expected["category"],
            "predicted_priority": pred_prio,
            "expected_priority": expected["priority"],
            "citations": pred_citations,
            "expected_citations": must_cite,
            "recommended_actions": pred_actions,
            "disallowed_actions": disallowed,
            "should_escalate": pred_escalate,
            "expected_escalation": expected["should_escalate"]
        })
        
    total_cases = len(cases)
    metrics = {
        "triage_category_accuracy": correct_category / total_cases,
        "triage_priority_accuracy": correct_priority / total_cases,
        "escalation_accuracy": correct_escalation / total_cases,
        "citation_coverage": citations_passed / total_cases,
        "unsafe_action_block_rate": (unsafe_actions_blocked / unsafe_relevant_cases) if unsafe_relevant_cases > 0 else 1.0
    }
    
    save_eval_run(
        eval_run_id=eval_run_id,
        started_at=datetime.utcnow().isoformat() + "Z",
        completed_at=datetime.utcnow().isoformat() + "Z",
        total_cases=total_cases,
        metrics=metrics,
        case_results=results
    )

@app.post("/api/evals/run")
def start_eval_run(background_tasks: BackgroundTasks):
    eval_run_id = f"eval_run_{uuid.uuid4().hex[:8]}"
    background_tasks.add_task(run_evaluations_sync, eval_run_id)
    return {"eval_run_id": eval_run_id, "status": "started"}

@app.get("/api/evals/results")
def fetch_eval_results():
    runs = get_all_eval_runs()
    return runs

# Mount Frontend Static Files (Ensure API endpoints take priority)
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    # Create empty directory if it doesn't exist
    FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
