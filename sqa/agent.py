"""SQL analytics agent: NL question -> SQL -> execute -> self-correct -> answer."""
from __future__ import annotations

import difflib
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from .db import introspect
from .llm import get_llm
from .parser import NLSQLParser

FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|attach|pragma|vacuum|replace)\b",
                       re.IGNORECASE)


@dataclass
class AgentResult:
    question: str
    sql: str
    columns: list[str]
    rows: list[tuple]
    summary: str
    mode: str
    attempts: int
    explanation: str = ""
    error: str | None = None
    trace: list[str] = field(default_factory=list)

    def render(self, max_rows: int = 12) -> str:
        out = [f"Q: {self.question}", f"SQL ({self.mode}, {self.attempts} attempt(s)): {self.sql}"]
        if self.error:
            out.append(f"ERROR: {self.error}")
            return "\n".join(out)
        widths = [max(len(str(c)), *(len(str(r[i])) for r in self.rows[:max_rows])) if self.rows
                  else len(str(c)) for i, c in enumerate(self.columns)]
        out.append(" | ".join(str(c).ljust(w) for c, w in zip(self.columns, widths)))
        out.append("-+-".join("-" * w for w in widths))
        for r in self.rows[:max_rows]:
            out.append(" | ".join(str(v).ljust(w) for v, w in zip(r, widths)))
        if len(self.rows) > max_rows:
            out.append(f"... ({len(self.rows)} rows total)")
        out.append(f"=> {self.summary}")
        return "\n".join(out)


class SQLAnalyticsAgent:
    def __init__(self, db_path: str | Path, use_llm: bool = True, max_attempts: int = 3):
        self.conn = sqlite3.connect(f"file:{Path(db_path)}?mode=ro", uri=True)
        self.schema = introspect(self.conn)
        self.parser = NLSQLParser(self.schema)
        self.llm = get_llm() if use_llm else None
        self.max_attempts = max_attempts

    def close(self) -> None:
        self.conn.close()

    # ---------- guarded execution ----------
    def execute(self, sql: str) -> tuple[list[str], list[tuple]]:
        if FORBIDDEN.search(sql):
            raise PermissionError("read-only agent: only SELECT statements are allowed")
        if not sql.strip().lower().startswith(("select", "with")):
            raise PermissionError("only SELECT/WITH queries are allowed")
        cur = self.conn.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        return cols, cur.fetchmany(500)

    # ---------- self-correction ----------
    def _repair(self, sql: str, error: str) -> str | None:
        m = re.search(r"no such column: ([\w.]+)", error)
        if m:
            bad = m.group(1).split(".")[-1]
            all_cols = {c for cols in self.schema.tables.values() for c in cols}
            fix = difflib.get_close_matches(bad, sorted(all_cols), n=1, cutoff=0.6)
            if fix:
                return re.sub(rf"\b{re.escape(bad)}\b", fix[0], sql)
        m = re.search(r"no such table: (\w+)", error)
        if m:
            bad = m.group(1)
            fix = difflib.get_close_matches(bad, list(self.schema.tables), n=1, cutoff=0.6)
            if fix:
                return re.sub(rf"\b{re.escape(bad)}\b", fix[0], sql)
        return None

    # ---------- answering ----------
    def ask(self, question: str) -> AgentResult:
        trace: list[str] = []
        if self.llm is not None:
            sql = self._llm_sql(question, trace)
            mode = "claude"
        else:
            parsed = self.parser.parse(question)
            sql, mode = parsed.sql, "offline-parser"
            trace.append(f"parser: {parsed.explanation}")
        attempts, error = 0, None
        while attempts < self.max_attempts:
            attempts += 1
            try:
                cols, rows = self.execute(sql)
                summary = self._summarize(question, cols, rows)
                return AgentResult(question, sql, cols, rows, summary, mode, attempts,
                                   trace=trace)
            except (sqlite3.Error, PermissionError) as exc:
                error = str(exc)
                trace.append(f"attempt {attempts} failed: {error}")
                fixed = None
                if self.llm is not None:
                    raw = self.llm.complete(
                        f"Schema:\n{self.schema.describe()}\n\nThe SQL below failed with error: "
                        f"{error}\n\nSQL: {sql}\n\nReturn ONLY the corrected SQLite SELECT.")
                    fixed = self._clean_sql(raw)
                if not fixed:
                    fixed = self._repair(sql, error)
                if not fixed or fixed == sql:
                    break
                sql = fixed
        return AgentResult(question, sql, [], [], "", mode, attempts, error=error, trace=trace)

    def _llm_sql(self, question: str, trace: list[str]) -> str:
        raw = self.llm.complete(
            f"Schema:\n{self.schema.describe()}\n\nQuestion: {question}\n\n"
            "Return ONLY one SQLite SELECT statement (no markdown, no commentary).",
            system="You translate analytics questions to a single safe SQLite SELECT.")
        sql = self._clean_sql(raw)
        trace.append("llm generated sql")
        return sql or self.parser.parse(question).sql

    @staticmethod
    def _clean_sql(raw: str) -> str | None:
        raw = raw.strip()
        m = re.search(r"```(?:sql)?\s*(.+?)```", raw, re.DOTALL)
        if m:
            raw = m.group(1).strip()
        return raw if raw.lower().startswith(("select", "with")) else None

    @staticmethod
    def _summarize(question: str, cols: list[str], rows: list[tuple]) -> str:
        if not rows:
            return "no rows matched"
        if len(rows) == 1 and len(cols) == 1:
            v = rows[0][0]
            return f"{cols[0]} = {v:,.2f}" if isinstance(v, float) else f"{cols[0]} = {v}"
        if len(cols) >= 2 and all(isinstance(r[-1], (int, float)) for r in rows[:5]):
            top = rows[0]
            total = sum(r[-1] for r in rows if isinstance(r[-1], (int, float)))
            return (f"{len(rows)} groups; top: {top[0]} ({top[-1]:,.2f}); "
                    f"total {total:,.2f}")
        return f"{len(rows)} rows returned"


def analytics_report(agent: SQLAnalyticsAgent, questions: list[str], path: Path) -> str:
    parts = ["# Analytics Report", ""]
    for q in questions:
        r = agent.ask(q)
        parts += [f"## {q}", "", "```", r.render(), "```", ""]
    text = "\n".join(parts)
    path.write_text(text, encoding="utf-8")
    return text
