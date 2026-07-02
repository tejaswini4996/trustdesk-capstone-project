# TrustDesk Capstone Pack

This folder contains a self-contained capstone package for learners building **TrustDesk**, an AI-first customer support operations backend.

The capstone is language agnostic. Learners may implement it in Node.js, Java, Python, Go, Ruby, or any backend stack they are comfortable with, as long as they satisfy the API, data, security, and evaluation requirements.

## Contents

- `TRUSTDESK_PROBLEM_STATEMENT.md` - learner-facing capstone problem statement.
- `docs/API_CONTRACT.md` - language-agnostic API contract and expected flows.
- `docs/DATA_MODEL.md` - suggested entities, relationships, and storage expectations.
- `docs/EVALUATION_GUIDE.md` - how to use the eval cases and what to measure.
- `data/knowledge_base/` - sample policy and support documents for retrieval.
- `data/customers.json` - fictional customer records.
- `data/orders.json` - fictional order records.
- `data/tickets.json` - support tickets with expected triage labels.
- `data/eval_cases.jsonl` - evaluation cases for answer quality, citations, routing, and guardrails.
- `data/tool_actions.json` - mock tool/action catalog for agentic workflows.
- `scripts/seed_trustdesk.py` - optional Python utility that creates a local SQLite database from the sample data.
- `scripts/run_baseline_retrieval.py` - optional Python utility that runs a simple keyword baseline over the seeded knowledge base.
- `scripts/validate_pack.py` - optional Python utility that validates that the package data is parseable and internally consistent.

## Quick Start For Instructors

From this folder:

```bash
python3 scripts/validate_pack.py
python3 scripts/seed_trustdesk.py --db trustdesk_seed.db
python3 scripts/run_baseline_retrieval.py --db trustdesk_seed.db
```

The scripts use only Python standard library modules.

Learners do not need to use these scripts or SQLite. They can load the raw files in `data/` into PostgreSQL, MySQL, MongoDB, Elasticsearch, Redis, a vector database, local files, or any other storage system they choose.

## Language-Agnostic Expectations

Every implementation should provide:

- A backend API matching the core flows in `docs/API_CONTRACT.md`.
- A persistent data model covering the entities in `docs/DATA_MODEL.md`.
- A retrieval layer over `data/knowledge_base/`.
- An AI/model adapter that can be mocked in tests.
- Guardrails for prompt injection, sensitive data leakage, unsafe tool use, and unsupported answers.
- An evaluation command, endpoint, or script that runs `data/eval_cases.jsonl` and reports results.

## Notes For Instructors

The dataset intentionally includes adversarial tickets and one adversarial knowledge-base document. Learners should not treat retrieved text or customer text as trusted instructions. Strong submissions should include prompt-injection defenses, citation checks, tool permissioning, human approval gates, and evaluation reports.
