# QueryMind — Natural Language to SQL Compiler Pipeline with Read-Only Safety

QueryMind is a natural language SQL translation engine structured as a true **Compiler Pipeline** (Lexer → Parser → Semantic Type Checker → AST Query Planner → Read-Only SQL Executor) rather than naive LLM prompt wrapper.

## Pipeline Passes

```
Natural Language Question: "Top 5 customers by revenue in Q3 2026"
               │
               ▼
[Lexical Analysis & Schema Introspection] (Tables, Foreign Keys, Column Types)
               │
               ▼
[Semantic AST Planner] (Join Graph Traversal, Aggregate Grouping, Date Filtering)
               │
               ▼
[Safety Validator & Guardrails] (Enforces read-only SELECT, blocks mutations & injections)
               │
               ▼
[Dialect SQL Code Emitter & Executor] ──► SQLite / Postgres Query Execution
```

## Usage

```bash
# Start interactive NL-to-SQL REPL
python -m nlsql --db output/ecommerce_analytics.db --interactive
```

## Tests

```bash
pytest tests/ -v
```
