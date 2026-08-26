# QueryMind — Natural Language SQL Analytics Agent

> Ask business questions. Get SQL answers. QueryMind introspects any SQLite database schema, translates plain-English questions to SQL, executes read-only queries, self-corrects on errors, and returns formatted result tables with one-line summaries.

## What QueryMind Does

- **Schema introspection** — auto-discovers tables, columns, foreign keys, low-cardinality values
- **NL-to-SQL translation** — two interchangeable backends: Claude API or rule-based template engine
- **Self-correction** — retries with rephrased SQL on execution error; explains the fix
- **Read-only safety** — query sandbox prevents any writes, deletes, or schema changes
- **Interactive REPL** — cmd.Cmd shell for iterative data exploration

## Architecture

```
SQLite Database
    └─> SchemaIntrospector  (tables, columns, FK graph, value samples)
    └─> NLToSQLTranslator   (Claude API or rule-based template engine)
    └─> QueryExecutor       (read-only sandbox)
    └─> SelfCorrector       (retry on error with rephrased SQL)
    └─> ResultFormatter     (tabular output + one-line summary)
    └─> AnalyticsREPL       (interactive cmd.Cmd shell)
```

## Quickstart

```bash
python -m sqa                              # launch interactive analytics REPL
python -m sqa query "top 10 customers by revenue" --db sales.db
python -m sqa demo
```

## Test

```bash
python tests/test_smoke.py
```

---

## 👤 Author & Contact

- **Author**: Nathaniel Gordon
- **Role**: Senior AI & Machine Learning Engineer
- **GitHub**: [github.com/nathaniel-gordon](https://github.com/nathaniel-gordon)
- **Portfolio / Upwork**: [upwork.com/freelancers/~015fe5a704f8943797](https://www.upwork.com/freelancers/~015fe5a704f8943797)
- **Email**: nathanielgordon346@gmail.com
- **Location**: Tallahassee, FL, USA
