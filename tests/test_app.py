import os
import sys
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

# Initialize database to make sure it exists before tests run
from backend.database import init_db, seed_db, get_connection
init_db()
seed_db()

from backend.app import app

client = TestClient(app)

def test_api_list_tickets():
    """Verify that we can list tickets."""
    response = client.get("/api/tickets")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 8
    assert data[0]["ticket_id"] == "tkt_9001"

def test_api_ticket_context():
    """Verify fetching ticket context (customer & order)."""
    response = client.get("/api/tickets/tkt_9001/context")
    assert response.status_code == 200
    data = response.json()
    assert "customer" in data
    assert "order" in data
    assert data["customer"]["customer_id"] == "cus_1001"
    assert data["order"]["order_id"] == "ord_5001"

def test_api_triage():
    """Verify AI triage endpoint works and creates a trace."""
    response = client.post("/api/tickets/tkt_9001/triage")
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "refund"
    assert data["priority"] == "medium"
    assert "run_id" in data
    
    # Verify trace exists
    trace_response = client.get(f"/api/traces/{data['run_id']}")
    assert trace_response.status_code == 200
    trace_data = trace_response.json()
    assert trace_data["run_type"] == "triage"

def test_api_draft_and_guardrails():
    """Verify draft reply generation and security guardrails."""
    # Test Normal case
    response = client.post("/api/tickets/tkt_9001/draft")
    assert response.status_code == 200
    data = response.json()
    assert "KB-REFUND-001" in data["citations"]
    assert data["guardrail"]["status"] == "passed"
    
    # Test adversarial coupon injection (tkt_9006)
    injection_response = client.post("/api/tickets/tkt_9006/draft")
    assert injection_response.status_code == 200
    inj_data = injection_response.json()
    assert inj_data["guardrail"]["status"] == "blocked"
    assert "KB-SECURITY-001" in inj_data["citations"]
    
    # Ensure tool actions recommended only has escalate_to_human
    actions = [a["tool_name"] for a in inj_data["recommended_actions"]]
    assert "issue_coupon" not in actions
    assert "escalate_to_human" in actions

def test_api_idempotency_and_rbac():
    """Verify action requests validate category, enforce idempotency and RBAC rules."""
    ticket_id = "tkt_9001" # Refund category
    
    # 1. Request valid tool action
    idempotency_key = "test-idemp-12345"
    payload = {
        "tool_name": "create_replacement_order",
        "payload": {
            "order_id": "ord_5001",
            "sku": "BG-AIRPODS-01",
            "reason": "Damaged test case",
            "idempotency_key": idempotency_key
        },
        "idempotency_key": idempotency_key
    }
    
    # Submit action
    response = client.post(f"/api/tickets/{ticket_id}/actions", json=payload)
    assert response.status_code == 200
    action_data = response.json()
    assert action_data["status"] == "approval_required"
    action_id = action_data["action_id"]
    
    # 2. Test Idempotency: Submit again with same key, should return the exact same action_id
    dup_response = client.post(f"/api/tickets/{ticket_id}/actions", json=payload)
    assert dup_response.status_code == 200
    assert dup_response.json()["action_id"] == action_id
    
    # 3. Test Category Mismatch: try to call a billing/refund tool on a shipping category ticket
    # tkt_9002 has expected_category = 'shipping'
    mismatch_payload = {
        "tool_name": "create_replacement_order", # allowed categories: refund, warranty
        "payload": {
            "order_id": "ord_5002",
            "sku": "BG-AIRPODS-01",
            "reason": "Shipping ticket category mismatch",
            "idempotency_key": "mismatch-idemp-456"
        },
        "idempotency_key": "mismatch-idemp-456"
    }
    mismatch_response = client.post("/api/tickets/tkt_9002/actions", json=mismatch_payload)
    assert mismatch_response.status_code == 400
    assert "not allowed for ticket category" in mismatch_response.json()["detail"]
    
    # 4. Test RBAC validation: Support agent tries to approve (unauthorized)
    # The default token is agent-token which maps to support_agent
    agent_response = client.post(f"/api/actions/{action_id}/approve")
    assert agent_response.status_code == 403
    assert "Manager or Admin role required" in agent_response.json()["detail"]
    
    # 5. Test RBAC: Support manager approves (authorized)
    manager_headers = {"Authorization": "Bearer manager-token"}
    manager_response = client.post(f"/api/actions/{action_id}/approve", headers=manager_headers)
    assert manager_response.status_code == 200
    assert manager_response.json()["status"] == "executed"
