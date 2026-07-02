# TrustDesk API Contract

This document describes the expected backend behavior without requiring any specific programming language or framework.

Learners may change route names, request shapes, or response shapes if they document the changes clearly. A strong submission should still support the flows below.

## Roles

- `support_agent`: Reviews tickets, drafts, and non-admin tool actions.
- `support_manager`: Approves sensitive actions and goodwill exceptions.
- `admin`: Manages knowledge-base ingestion, model configuration, eval runs, and audit logs.

## Core Resources

- Customer
- Order
- Ticket
- Knowledge document
- Draft reply
- Tool action request
- Approval
- Agent run trace
- Feedback
- Eval run

## Authentication

Implement a realistic authentication mechanism for the chosen stack.

Minimum expectation:

- Login or token-based API access.
- Role-aware authorization.
- Users must not read or mutate tickets outside their allowed organization or scope.

## Required Flows

### 1. Ingest Knowledge Documents

Expected behavior:

- Accept one or more documents.
- Store document metadata and content.
- Prepare the document for retrieval.
- Preserve source document IDs such as `KB-REFUND-001`.

Example request:

```json
{
  "documents": [
    {
      "doc_id": "KB-REFUND-001",
      "title": "Refund and Return Policy",
      "content": "...",
      "source_path": "data/knowledge_base/refund_policy.md"
    }
  ]
}
```

Example response:

```json
{
  "ingested": 1,
  "document_ids": ["KB-REFUND-001"]
}
```

### 2. Search Knowledge Base

Expected behavior:

- Accept a natural-language query.
- Return ranked documents or chunks.
- Include document IDs, titles, snippets, and relevance scores if available.

Example response:

```json
{
  "query": "damaged item replacement",
  "results": [
    {
      "doc_id": "KB-REFUND-001",
      "title": "Refund and Return Policy",
      "snippet": "For damaged or defective items reported within the return window...",
      "score": 0.87
    }
  ]
}
```

### 3. Create Ticket

Expected behavior:

- Store incoming ticket details.
- Link customer and order when provided.
- Keep the original customer message unchanged for auditability.

Example request:

```json
{
  "customer_id": "cus_1001",
  "order_id": "ord_5001",
  "channel": "email",
  "subject": "Received damaged earbuds",
  "body": "My BlueBuds Air arrived with the left earbud cracked."
}
```

### 4. Triage Ticket

Expected behavior:

- Classify category, priority, sentiment, and escalation need.
- Use retrieved context if useful.
- Store the triage output and trace.

Example response:

```json
{
  "ticket_id": "tkt_9001",
  "category": "refund",
  "priority": "medium",
  "sentiment": "frustrated",
  "should_escalate": false,
  "reason_summary": "Damaged physical product reported within the return window.",
  "run_id": "run_123"
}
```

### 5. Generate Draft Reply

Expected behavior:

- Retrieve relevant documents.
- Generate a grounded support draft.
- Include citations using document IDs.
- Refuse or escalate unsupported or unsafe requests.
- Store the draft and the agent run trace.

Example response:

```json
{
  "draft_id": "draft_123",
  "ticket_id": "tkt_9001",
  "status": "generated",
  "body": "I am sorry the BlueBuds Air arrived damaged...",
  "citations": ["KB-REFUND-001"],
  "recommended_actions": [
    {
      "tool_name": "create_replacement_order",
      "requires_human_approval": true,
      "reason": "Damaged physical item reported within return window."
    }
  ],
  "run_id": "run_124"
}
```

### 6. Approve Or Reject Draft

Expected behavior:

- Allow a support agent to approve, edit, or reject a draft.
- Store reviewer ID, timestamp, and reason.
- Only approved drafts may be sent.

### 7. Request Tool Action

Expected behavior:

- Validate the tool exists.
- Validate required fields.
- Validate that the tool is allowed for the ticket category.
- Enforce idempotency.
- Require human approval for sensitive actions.

Example action request:

```json
{
  "ticket_id": "tkt_9001",
  "tool_name": "create_replacement_order",
  "payload": {
    "order_id": "ord_5001",
    "sku": "BG-AIRPODS-01",
    "reason": "Damaged on arrival",
    "idempotency_key": "tkt_9001-replacement-1"
  }
}
```

### 8. Approve And Execute Tool Action

Expected behavior:

- Support managers approve sensitive actions.
- Low-risk allowed actions may execute automatically if your design permits it.
- Store execution status, result, errors, and retry attempts.

### 9. Submit Feedback

Expected behavior:

- Support agents can rate draft quality and triage quality.
- Store corrected response text where provided.
- Track common failure reasons.

### 10. Run Evaluations

Expected behavior:

- Run all or selected cases from `data/eval_cases.jsonl`.
- Report triage accuracy, citation coverage, allowed/disallowed action safety, and escalation behavior.
- Store eval run summaries.

Example response:

```json
{
  "eval_run_id": "eval_run_001",
  "total_cases": 8,
  "triage_accuracy": 0.875,
  "citation_coverage": 1.0,
  "unsafe_action_block_rate": 1.0,
  "escalation_accuracy": 0.875
}
```

## Error Handling

Use consistent API errors. At minimum, represent:

- Validation errors.
- Authentication failures.
- Authorization failures.
- Missing resources.
- Guardrail failures.
- Tool execution failures.
- AI provider failures or timeouts.

## Idempotency

Tool actions must use idempotency keys so retries do not create duplicate refunds, replacements, coupons, or escalations.

## Auditability

Every AI-generated answer, triage decision, retrieval result, tool recommendation, approval, and tool execution should be traceable to a ticket and reviewer or system actor.

