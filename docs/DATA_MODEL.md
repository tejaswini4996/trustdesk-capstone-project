# TrustDesk Data Model

This is a language-agnostic data model. Learners may use SQL, NoSQL, document stores, vector databases, search indexes, or local files, as long as they preserve the core entities and relationships.

## Source Data Files

- `data/customers.json`
- `data/orders.json`
- `data/tickets.json`
- `data/tool_actions.json`
- `data/eval_cases.jsonl`
- `data/knowledge_base/*.md`

These files are the canonical seed data. The optional SQLite seed script is only one possible way to load them.

## Entities

### Customer

Required fields:

- `customer_id`
- `name`
- `email`
- `tier`
- `country`
- `created_at`
- `verified`
- `tags`

### Order

Required fields:

- `order_id`
- `customer_id`
- `status`
- `placed_at`
- `delivered_at`
- `eligible_return_until`
- `total`
- `currency`
- `payment_status`
- `tracking_number`
- `items`

Relationship:

- Many orders belong to one customer.

### Ticket

Required fields:

- `ticket_id`
- `customer_id`
- `order_id`
- `channel`
- `subject`
- `body`
- `created_at`
- `status`

Seed-only expected labels:

- `expected_category`
- `expected_priority`
- `expected_sentiment`
- `expected_escalation`
- `expected_actions`

These labels are for testing/evaluation. Production logic should not depend on them.

### Knowledge Document

Required fields:

- `doc_id`
- `title`
- `content`
- `source_path`
- `version`
- `audience`
- `updated_at` or equivalent ingestion timestamp

Recommended derived fields:

- chunks
- embeddings
- search terms
- checksum

### Draft Reply

Required fields:

- `draft_id`
- `ticket_id`
- `status`
- `body`
- `citations`
- `created_by`
- `created_at`
- `updated_at`

Suggested statuses:

- `generated`
- `edited`
- `approved`
- `rejected`
- `sent`

### Tool Action Request

Required fields:

- `action_id`
- `ticket_id`
- `tool_name`
- `payload`
- `risk_level`
- `requires_human_approval`
- `status`
- `idempotency_key`
- `created_at`

Suggested statuses:

- `requested`
- `approval_required`
- `approved`
- `rejected`
- `executed`
- `failed`
- `cancelled`

### Approval

Required fields:

- `approval_id`
- `action_id` or `draft_id`
- `reviewer_id`
- `decision`
- `reason`
- `created_at`

Suggested decisions:

- `approved`
- `rejected`
- `needs_changes`

### Agent Run Trace

Required fields:

- `run_id`
- `ticket_id`
- `run_type`
- `status`
- `model_provider`
- `model_name`
- `prompt_version`
- `retrieved_doc_ids`
- `tool_calls`
- `guardrail_results`
- `latency_ms`
- `token_usage`
- `cost_estimate`
- `created_at`

Run types:

- `triage`
- `draft_reply`
- `tool_recommendation`
- `eval_case`

### Feedback

Required fields:

- `feedback_id`
- `ticket_id`
- `draft_id`
- `rating`
- `reason`
- `corrected_response`
- `created_at`

### Eval Run

Required fields:

- `eval_run_id`
- `started_at`
- `completed_at`
- `total_cases`
- `metrics`
- `case_results`

## Tool Catalog

The tool catalog lives in `data/tool_actions.json`.

Every implementation should enforce:

- Required payload fields.
- Allowed ticket categories.
- Risk level.
- Human approval requirement.
- Max coupon amount where present.
- Idempotency key uniqueness.

## Storage Guidance

Acceptable storage choices include:

- PostgreSQL or MySQL for relational data.
- MongoDB or another document store.
- SQLite for a local demo.
- Elasticsearch, OpenSearch, Typesense, or database full-text search for retrieval.
- pgvector, Qdrant, Pinecone, Weaviate, Chroma, or similar vector stores for semantic retrieval.

The grading focus is not the specific database. The grading focus is whether the data is modeled clearly, persists correctly, and supports auditability, retrieval, approval, and evaluation flows.

