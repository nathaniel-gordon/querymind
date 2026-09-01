<div align="center">

# 🧭 QueryMind

**Ask questions in plain English. Get back exact data from your database — safely.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-Passing-22c55e?style=for-the-badge&logo=pytest&logoColor=white)](tests/)
[![Domain](https://img.shields.io/badge/Domain-Text-to-SQL%20%2F%20Compiler-8b5cf6?style=for-the-badge)](https://github.com/nathaniel-gordon/querymind)

<br/>

*Natural Language to SQL compiler pipeline with strict AST validation and read-only safety guardrails. Implements schema introspection, join-graph resolution, semantic AST planning, and dialect-specific code emission for SQLite and Postgres.*

</div>

---

## 🧠 What Is This?

> **For non-technical readers:** Querying a company database usually requires writing complex SQL code with table joins and aggregations. QueryMind lets anyone ask questions in plain English (like *"Show me the top 5 customers by revenue in Q3 2026"*). It translates the question into database code, runs it, and shows you the table of results. It includes ironclad safety locks that guarantee it can only *read* data — it is mathematically impossible for QueryMind to modify, delete, or drop any of your tables.

---

## 🏗️ Compiler Pipeline Architecture

Unlike naive Text-to-SQL wrappers that blindly pass user text to an LLM and execute the raw response, QueryMind is structured as a **Multi-Pass Compiler Pipeline**.

```
💬 Natural Language Question
"Top 5 customers by revenue in Q3 2026"
                 │
                 ▼
🔍 Pass 1: Lexical Analysis & Schema Introspection
   ├── Extracts Table Metadata, Foreign Keys, and Column Datatypes
   └── Discovers Entity Relationships via Schema Graph
                 │
                 ▼
🗺️ Pass 2: Semantic AST Query Planner
   ├── Traverses Join Graph (Shortest Path foreign key resolution)
   ├── Identifies Aggregations (SUM, COUNT, AVG) & Groupings
   └── Normalizes Temporal Filters (Q3 2026 → 2026-07-01 to 2026-09-30)
                 │
                 ▼
🛡️ Pass 3: Safety AST Validator & Guardrails
   ├── Enforces Strict Read-Only Policy (Rejects DROP, DELETE, UPDATE, ALTER)
   ├── Blocks Multi-Statement Injections & Tautological Bypasses
   └── Applies Automatic Row-Limit Safeguards (LIMIT 1000)
                 │
                 ▼
⚡ Pass 4: Dialect Code Emitter & Executor
   ├── Emits Dialect-Specific SQL (SQLite / PostgreSQL / MySQL)
   └── Executes Query in Isolated Read-Only Connection
                 │
                 ▼
📊 Clean Tabular Output + Generated SQL Audit Trace
```

---

## 🛡️ Ironclad Safety & Guardrail Features

| Threat Vector | Naive LLM SQL Wrapper | QueryMind Compiler |
|---|---|---|
| 💥 **Data Mutation (`DROP`, `DELETE`)** | ❌ Vulnerable to prompt injection | ✅ **Blocked at AST level** (non-SELECT statements rejected before DB) |
| 🕳️ **SQL Injection** | ❌ Vulnerable to delimiter tampering | ✅ **AST Tokenizer** isolates user inputs into parameterized literals |
| 💣 **Unbounded Queries** | ❌ May crash memory with millions of rows | ✅ **Automatic `LIMIT` Clamping** enforced on all query ASTs |
| 🔗 **Hallucinated Joins** | ❌ Hallucinates non-existent foreign keys | ✅ **Join-Graph Solver** verifies paths along actual foreign key edges |

---

## 📺 Sample Session

```
User Query: "Which product categories generated the most revenue in 2026?"

Compiled SQL:
SELECT 
    c.category_name,
    ROUND(SUM(oi.quantity * oi.unit_price), 2) AS total_revenue
FROM categories c
JOIN products p ON c.category_id = p.category_id
JOIN order_items oi ON p.product_id = oi.product_id
JOIN orders o ON oi.order_id = o.order_id
WHERE o.order_date >= '2026-01-01' AND o.order_date <= '2026-12-31'
GROUP BY c.category_name
ORDER BY total_revenue DESC
LIMIT 10;

Results:
┌────────────────────┬───────────────┐
│ category_name      │ total_revenue │
├────────────────────┼───────────────┤
│ Enterprise Cloud   │ $1,420,500.00 │
│ Security Hardware  │ $980,250.00   │
│ Developer Tooling  │ $640,120.50   │
│ Storage Systems    │ $310,800.00   │
└────────────────────┴───────────────┘
Execution Time: 4.2ms | Safety Status: VERIFIED (Read-Only)
```

---

## 🚀 Getting Started

```bash
git clone https://github.com/nathaniel-gordon/querymind
cd querymind
pip install -e .
```

### Run the Interactive REPL

```bash
# Start interactive NL-to-SQL session against the bundled retail database
python -m sqa --db output/retail.db --interactive
```

### Run Single Query via CLI

```bash
# Execute a single question and output Markdown table
python -m sqa --db output/retail.db --query "What is our total revenue for 2026?"
```

### Run Tests

```bash
pytest tests/ -v
```

---

## 📁 Project Structure

```
querymind/
├── sqa/
│   ├── agent.py            # High-level pipeline coordinator & formatting
│   ├── db.py               # Database connector, schema introspection & execution
│   ├── llm.py              # LLM backend integration & prompt templates
│   ├── parser.py           # AST parser, schema join graph, & safety validator
│   ├── __init__.py
│   └── __main__.py         # CLI entrypoint and interactive REPL
├── output/
│   ├── retail.db           # Sample e-commerce analytics SQLite database
│   └── analytics_report.md # Generated query report
└── tests/
    └── test_smoke.py       # SQL compiler & safety guardrail test suite
```

---

<div align="center">

*Built by [Nathaniel Gordon](https://github.com/nathaniel-gordon)*

</div>
