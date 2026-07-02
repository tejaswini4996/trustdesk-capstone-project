# AI-First Software Engineering Capstone - Case Study

## TrustDesk: AI Support Operations Agent

**Author:** Airtribe

## Background & Objective

Modern support teams handle thousands of repetitive but high-stakes customer conversations. A good support system must answer quickly, cite the right policy, understand customer and order context, route edge cases to humans, and avoid taking risky actions without approval.

Traditional chatbots usually fail because they either hallucinate answers, ignore company policy, or cannot safely act on behalf of support teams. TrustDesk is an AI-first product where the AI is not just a text generator. It must retrieve policy context, classify tickets, decide whether it has enough evidence, suggest or execute allowed tools, and leave a complete audit trail.

The objective is to build a reliable AI support operations platform that can:

- Ingest company support documents and retrieve relevant policy context.
- Triage incoming support tickets by intent, priority, sentiment, and escalation need.
- Generate grounded draft replies with citations from the knowledge base.
- Suggest safe operational actions such as replacement, refund review, coupon creation, or escalation.
- Require human approval for sensitive actions.
- Defend against prompt injection, unsupported policy claims, PII leakage, and excessive agency.
- Track feedback, evaluations, costs, traces, and support outcomes.

## Language and Stack

This project is intentionally language agnostic. You may implement it in Node.js, Java, Python, Go, Ruby, or any stack of your choice.

You are free to choose your framework, database, queue, retrieval approach, vector store, and AI provider. Free-tier APIs (for example Gemini or Groq) or locally hosted models (for example via Ollama) are acceptable, and tests may run against a mocked model adapter. Your choices must be documented, and the system must satisfy the functional, security, and evaluation requirements described below.

The provided Python scripts are optional local utilities. They are not part of the required implementation stack.

## Key Features

### 1. Knowledge Base Ingestion and Retrieval

- Ingest Markdown, text, or JSON support documents.
- Store document metadata such as document ID, title, source, version, and updated timestamp.
- Chunk large documents for retrieval.
- Implement keyword, vector, or hybrid search.
- Return citations for every policy-backed answer.
- Support re-ingestion when a policy document changes.

### 2. Ticket Intake and Triage

- Provide APIs to create and fetch support tickets.
- Classify each ticket into categories such as `shipping`, `refund`, `warranty`, `billing`, `account_security`, or `general`.
- Assign priority such as `low`, `medium`, `high`, or `urgent`.
- Detect sentiment and escalation needs.
- Attach customer and order context where available.
- Store triage decisions and model reasoning summaries for auditability.

### 3. AI Draft Replies With Citations

- Generate a draft support response using ticket content, customer/order context, and retrieved policy documents.
- Include citation references to the documents used.
- Refuse or escalate when the answer is not supported by retrieved policy.
- Avoid exposing internal-only notes, hidden prompts, secrets, or irrelevant customer data.
- Support draft lifecycle states: `generated`, `edited`, `approved`, `rejected`, and `sent`.

### 4. Tool Actions and Human Approval

- Implement a mock tool registry for support operations.
- Example tools:
  - `create_replacement_order`
  - `start_refund_review`
  - `issue_coupon`
  - `open_carrier_investigation`
  - `escalate_to_human`
  - `lock_account`
- The AI may recommend actions, but sensitive actions must require human approval.
- Store tool call requests, approval decisions, execution status, and idempotency keys.
- Prevent the AI from invoking tools that are not allowed for the ticket type or user role.

### 5. Guardrails and Security

- Detect prompt-injection attempts in tickets and retrieved documents.
- Treat customer messages and retrieved content as untrusted input.
- Prevent sensitive information disclosure, including API keys, system prompts, internal policy notes, or unrelated PII.
- Enforce user/role authorization when reading tickets, customers, orders, and documents.
- Add limits for token usage, retrieval size, tool calls, and repeated retries.
- Provide a fallback path to human escalation when guardrails fail.

### 6. Feedback and Learning Loop

- Let support agents rate AI drafts and triage quality.
- Store corrected responses and final human-approved replies.
- Track common failure reasons such as wrong citation, unsupported refund, missing context, or unsafe action.
- Use feedback data in evaluation reports or future prompt/retrieval improvements.

### 7. Observability and Evaluation

- Log each AI run with:
  - ticket ID
  - retrieved document IDs
  - model/provider used
  - prompt/template version
  - tool calls requested
  - guardrail results
  - latency
  - token/cost estimate if available
- Build an evaluation command or endpoint that runs the provided eval cases.
- Report accuracy for triage, citation coverage, refusal/escalation behavior, and tool-action safety.

### 8. Frontend Demo Experience

- Build a lightweight frontend for support agents.
- You may vibe-code or AI-assist the frontend.
- The UI should let a reviewer:
  - view the ticket queue,
  - open a ticket with customer and order context,
  - trigger triage,
  - generate and review an AI draft,
  - inspect citations,
  - approve, reject, or edit a draft,
  - approve or reject sensitive tool actions,
  - view evaluation results.
- The frontend does not need to be visually elaborate, but it should make the core workflow easy to demo.

## Technical Requirements

- Expose core functionality as RESTful APIs or a clearly documented equivalent HTTP API.
- Use a reliable persistent store for tickets, customers, orders, documents, drafts, tool calls, approvals, traces, and feedback.
- Implement authentication and authorization for customer-support users, admins, and reviewers.
- Implement a retrieval layer using either:
  - database full-text search,
  - a vector database,
  - a hybrid approach,
  - or a clearly documented local substitute.
- Keep the AI provider integration behind an adapter so it can be mocked in tests.
- Use retries and idempotency for external tool actions.
- Ensure sensitive actions require explicit human approval.
- Provide automated tests for critical flows and guardrails.
- Design for scalability: ingestion, ticket triage, AI generation, and evaluations should not block unrelated requests.
- Provide one command, endpoint, or documented process to run the supplied eval cases and produce an evaluation summary.
- Do not depend on any specific programming language, framework, or hosted AI provider for the core design.

## Suggested API Surface

You may design your own API shape, but a complete solution should cover flows similar to these:

- `POST /auth/login`
- `POST /documents/ingest`
- `GET /documents/search?q=...`
- `POST /tickets`
- `GET /tickets/{ticketId}`
- `POST /tickets/{ticketId}/triage`
- `POST /tickets/{ticketId}/draft-reply`
- `POST /drafts/{draftId}/approve`
- `POST /drafts/{draftId}/reject`
- `POST /tool-actions`
- `POST /tool-actions/{actionId}/approve`
- `POST /tool-actions/{actionId}/execute`
- `POST /feedback`
- `GET /agent-runs/{runId}`
- `POST /eval-runs`
- `GET /eval-runs/{evalRunId}`

## Suggested Milestones

You may plan your own schedule, but this staging keeps scope manageable:

1. **Core platform:** Auth, tickets, customers, orders, persistence, knowledge-base ingestion.
2. **Retrieval and triage:** Knowledge-base search, ticket triage with stored traces.
3. **Grounded drafts:** Draft replies with citations, refusal/escalation for unsupported requests, draft approval lifecycle.
4. **Tools and guardrails:** Tool registry, approval gates, idempotency, prompt-injection defenses.
5. **Frontend and polish:** Support-agent UI, eval runner over `data/eval_cases.jsonl`, evaluation report, observability, documentation, demo video.

**Minimum viable submission:** knowledge-base ingestion and retrieval, ticket triage, draft replies with citations, at least one approval-gated tool action, a lightweight frontend, guardrails that handle the provided adversarial cases, and the eval runner with a report. Everything beyond this — including all Optional Extensions — strengthens the submission but should not come before a working core.

## Provided Starter Dataset

This capstone pack includes:

- Fictional customers and orders.
- Support tickets with expected triage labels.
- Policy documents for refunds, shipping, warranty, account security, coupons, and support playbooks.
- Eval cases covering ordinary support tickets, unsupported requests, and adversarial prompt injection.
- A mock tool-action catalog.
- Raw files that can be loaded into any database or storage system.
- Optional Python scripts to seed a local SQLite database and run a retrieval baseline.

You may extend the dataset, but you must document any added data and how it affects evaluation.

## Assessment Criteria

- **Functionality:** Does the system meet the core support workflows end to end?
- **AI Quality:** Are responses grounded in policy, cited correctly, and appropriately escalated when uncertain?
- **Agentic Design:** Are tool actions modeled cleanly with permissions, idempotency, approval, and traceability?
- **Security and Guardrails:** Does the system defend against prompt injection, PII leakage, unsupported actions, and excessive agency?
- **Evaluation:** Does the project include repeatable evals and a clear report of strengths and failures?
- **System Design:** Is the system modular, scalable, fault-tolerant, and easy to extend?
- **Code Quality:** Is the code clean, organized, tested, and maintainable?
- **Documentation:** Does the README explain setup, API usage, architecture, design decisions, and known limitations?
- **Presentation:** Does the demo clearly show AI triage, grounded answering, approval gates, guardrails, and evaluation results?

## Deliverables

1. Final functional product with an API and lightweight frontend.
2. README with setup instructions, API documentation, architecture, and design decisions.
3. Public GitHub repository link.
4. Seeded demo data and instructions to reproduce the demo.
5. Evaluation report showing performance on the provided eval cases.
6. Explainer video demonstrating the project, including at least one adversarial or unsafe request being handled correctly.

## Optional Extensions

- Slack, Gmail, or Intercom-style ticket ingestion.
- Real vector database integration.
- Multi-tenant organization support.
- Admin dashboard for eval runs and model traces.
- Policy versioning and answer replay against older policy versions.
- Cost controls per organization or support agent.
- Red-team dashboard for prompt-injection and jailbreak attempts.
