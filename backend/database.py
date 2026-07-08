import os
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "trustdesk.db"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        
        # Create Tables
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                tier TEXT NOT NULL,
                country TEXT NOT NULL,
                created_at TEXT NOT NULL,
                verified INTEGER NOT NULL,
                tags_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL REFERENCES customers(customer_id),
                status TEXT NOT NULL,
                placed_at TEXT NOT NULL,
                delivered_at TEXT,
                eligible_return_until TEXT,
                total INTEGER NOT NULL,
                currency TEXT NOT NULL,
                payment_status TEXT NOT NULL,
                tracking_number TEXT,
                items_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL REFERENCES customers(customer_id),
                order_id TEXT REFERENCES orders(order_id),
                channel TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                expected_category TEXT,
                expected_priority TEXT,
                expected_sentiment TEXT,
                expected_escalation INTEGER,
                expected_actions_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS knowledge_documents (
                doc_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source_path TEXT NOT NULL,
                content TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS eval_cases (
                case_id TEXT PRIMARY KEY,
                ticket_id TEXT REFERENCES tickets(ticket_id),
                input TEXT NOT NULL,
                expected_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tool_action_catalog (
                tool_name TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                requires_human_approval INTEGER NOT NULL,
                allowed_categories_json TEXT NOT NULL,
                required_fields_json TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS agent_runs (
                run_id TEXT PRIMARY KEY,
                ticket_id TEXT REFERENCES tickets(ticket_id),
                run_type TEXT NOT NULL,
                status TEXT NOT NULL,
                retrieved_doc_ids_json TEXT NOT NULL DEFAULT '[]',
                tool_calls_json TEXT NOT NULL DEFAULT '[]',
                guardrail_results_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS feedback (
                feedback_id TEXT PRIMARY KEY,
                ticket_id TEXT REFERENCES tickets(ticket_id),
                rating INTEGER NOT NULL,
                reason TEXT,
                corrected_response TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS draft_replies (
                draft_id TEXT PRIMARY KEY,
                ticket_id TEXT NOT NULL REFERENCES tickets(ticket_id),
                status TEXT NOT NULL,
                body TEXT NOT NULL,
                citations_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS tool_action_requests (
                action_id TEXT PRIMARY KEY,
                ticket_id TEXT NOT NULL REFERENCES tickets(ticket_id),
                tool_name TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                requires_human_approval INTEGER NOT NULL,
                status TEXT NOT NULL,
                idempotency_key TEXT UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                executed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS approvals (
                approval_id TEXT PRIMARY KEY,
                action_id TEXT REFERENCES tool_action_requests(action_id),
                draft_id TEXT REFERENCES draft_replies(draft_id),
                reviewer_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                reason TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS eval_runs (
                eval_run_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                total_cases INTEGER NOT NULL,
                metrics_json TEXT NOT NULL,
                case_results_json TEXT NOT NULL
            );
        """)
        
        try:
            conn.executescript("""
                CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_documents_fts
                USING fts5(doc_id UNINDEXED, title, content);
            """)
        except sqlite3.OperationalError:
            pass
            
        conn.commit()
    finally:
        conn.close()

def seed_db():
    conn = get_connection()
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM customers")
        if cursor.fetchone()[0] > 0:
            print("Database already seeded.")
            return

        print("Seeding database...")
        
        def load_json(filename):
            with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
                return json.load(f)

        def load_jsonl(filename):
            rows = []
            with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        rows.append(json.loads(line))
            return rows

        customers = load_json("customers.json")
        for row in customers:
            conn.execute(
                """
                INSERT INTO customers
                (customer_id, name, email, tier, country, created_at, verified, tags_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["customer_id"],
                    row["name"],
                    row["email"],
                    row["tier"],
                    row["country"],
                    row["created_at"],
                    int(row["verified"]),
                    json.dumps(row["tags"]),
                ),
            )

        orders = load_json("orders.json")
        for row in orders:
            conn.execute(
                """
                INSERT INTO orders
                (order_id, customer_id, status, placed_at, delivered_at, eligible_return_until,
                 total, currency, payment_status, tracking_number, items_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["order_id"],
                    row["customer_id"],
                    row["status"],
                    row["placed_at"],
                    row.get("delivered_at"),
                    row.get("eligible_return_until"),
                    row["total"],
                    row["currency"],
                    row["payment_status"],
                    row.get("tracking_number"),
                    json.dumps(row["items"]),
                ),
            )

        tickets = load_json("tickets.json")
        for row in tickets:
            conn.execute(
                """
                INSERT INTO tickets
                (ticket_id, customer_id, order_id, channel, subject, body, created_at, status,
                 expected_category, expected_priority, expected_sentiment, expected_escalation,
                 expected_actions_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["ticket_id"],
                    row["customer_id"],
                    row.get("order_id"),
                    row["channel"],
                    row["subject"],
                    row["body"],
                    row["created_at"],
                    row["status"],
                    row.get("expected_category"),
                    row.get("expected_priority"),
                    row.get("expected_sentiment"),
                    int(row.get("expected_escalation", False)),
                    json.dumps(row.get("expected_actions", [])),
                ),
            )

        kb_dir = DATA_DIR / "knowledge_base"
        for path in sorted(kb_dir.glob("*.md")):
            content = path.read_text(encoding="utf-8")
            
            doc_id = None
            for line in content.splitlines():
                if line.lower().startswith("doc id:"):
                    doc_id = line.split(":", 1)[1].strip()
                    break
            if not doc_id:
                doc_id = path.stem.upper()
                
            title = path.stem
            for line in content.splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break

            conn.execute(
                """
                INSERT INTO knowledge_documents (doc_id, title, source_path, content)
                VALUES (?, ?, ?, ?)
                """,
                (doc_id, title, str(path.relative_to(DATA_DIR.parent)), content),
            )
            
            try:
                conn.execute(
                    """
                    INSERT INTO knowledge_documents_fts (doc_id, title, content)
                    VALUES (?, ?, ?)
                    """,
                    (doc_id, title, content),
                )
            except sqlite3.OperationalError:
                pass

        tools = load_json("tool_actions.json")
        for row in tools:
            metadata = {
                k: v
                for k, v in row.items()
                if k not in {"tool_name", "description", "risk_level", "requires_human_approval", "allowed_categories", "required_fields"}
            }
            conn.execute(
                """
                INSERT INTO tool_action_catalog
                (tool_name, description, risk_level, requires_human_approval,
                 allowed_categories_json, required_fields_json, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["tool_name"],
                    row["description"],
                    row["risk_level"],
                    int(row["requires_human_approval"]),
                    json.dumps(row["allowed_categories"]),
                    json.dumps(row["required_fields"]),
                    json.dumps(metadata),
                ),
            )

        eval_cases = load_jsonl("eval_cases.jsonl")
        for row in eval_cases:
            conn.execute(
                """
                INSERT INTO eval_cases (case_id, ticket_id, input, expected_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    row["case_id"],
                    row["ticket_id"],
                    row["input"],
                    json.dumps(row["expected"]),
                ),
            )

        conn.commit()
        print("Database seeded successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        conn.close()

# DATABASE QUERY HELPERS
def get_ticket(ticket_id):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_customer(customer_id):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_order(order_id):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_tool(tool_name):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM tool_action_catalog WHERE tool_name = ?", (tool_name,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def save_agent_run(run_id, ticket_id, run_type, status, retrieved_doc_ids, tool_calls, guardrail_results):
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO agent_runs
            (run_id, ticket_id, run_type, status, retrieved_doc_ids_json, tool_calls_json, guardrail_results_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                ticket_id,
                run_type,
                status,
                json.dumps(retrieved_doc_ids),
                json.dumps(tool_calls),
                json.dumps(guardrail_results)
            )
        )
        conn.commit()
    finally:
        conn.close()

def get_agent_run(run_id):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM agent_runs WHERE run_id = ?", (run_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def save_draft(draft_id, ticket_id, status, body, citations):
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO draft_replies
            (draft_id, ticket_id, status, body, citations_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (draft_id, ticket_id, status, body, json.dumps(citations))
        )
        conn.commit()
    finally:
        conn.close()

def get_latest_draft_for_ticket(ticket_id):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM draft_replies WHERE ticket_id = ? ORDER BY created_at DESC LIMIT 1",
            (ticket_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def save_tool_action_request(action_id, ticket_id, tool_name, payload, risk_level, requires_human_approval, status, idempotency_key):
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO tool_action_requests
            (action_id, ticket_id, tool_name, payload_json, risk_level, requires_human_approval, status, idempotency_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action_id,
                ticket_id,
                tool_name,
                json.dumps(payload),
                risk_level,
                int(requires_human_approval),
                status,
                idempotency_key
            )
        )
        conn.commit()
    finally:
        conn.close()

def get_tool_action_request(action_id):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM tool_action_requests WHERE action_id = ?", (action_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_tool_action_by_idempotency(idempotency_key):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM tool_action_requests WHERE idempotency_key = ?", (idempotency_key,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def update_tool_action_request_status(action_id, status, executed_at=None):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE tool_action_requests SET status = ?, executed_at = ? WHERE action_id = ?",
            (status, executed_at, action_id)
        )
        conn.commit()
    finally:
        conn.close()

def save_approval(approval_id, action_id, draft_id, reviewer_id, decision, reason):
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO approvals (approval_id, action_id, draft_id, reviewer_id, decision, reason)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (approval_id, action_id, draft_id, reviewer_id, decision, reason)
        )
        conn.commit()
    finally:
        conn.close()

def save_eval_run(eval_run_id, started_at, completed_at, total_cases, metrics, case_results):
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO eval_runs
            (eval_run_id, started_at, completed_at, total_cases, metrics_json, case_results_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                eval_run_id,
                started_at,
                completed_at,
                total_cases,
                json.dumps(metrics),
                json.dumps(case_results)
            )
        )
        conn.commit()
    finally:
        conn.close()

def get_latest_eval_run():
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM eval_runs ORDER BY completed_at DESC LIMIT 1").fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_all_eval_runs():
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM eval_runs ORDER BY completed_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    seed_db()
