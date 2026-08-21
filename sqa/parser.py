"""Deterministic schema-driven NL -> SQL semantic parser.

Handles the common analytics grammar:
  aggregates (count / sum / total / average / max / min), derived metrics (revenue),
  group-by ("by X", "per X"), top-N ("top 5 ..."), value filters ("in Germany",
  "completed orders"), year filters ("in 2024"), monthly trends ("monthly", "per month").
Joins are resolved automatically over the foreign-key graph (BFS shortest path).
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

from .db import Schema

METRIC_SYNONYMS = {
    "revenue": ("SUM", "quantity * unit_price"),
    "sales": ("SUM", "quantity * unit_price"),
    "spend": ("SUM", "quantity * unit_price"),
    "quantity": ("SUM", "quantity"),
    "units": ("SUM", "quantity"),
}
AGG_WORDS = {
    "count": "COUNT", "number": "COUNT", "how many": "COUNT",
    "total": "SUM", "sum": "SUM",
    "average": "AVG", "avg": "AVG", "mean": "AVG",
    "max": "MAX", "maximum": "MAX", "highest": "MAX",
    "min": "MIN", "minimum": "MIN", "lowest": "MIN",
}


@dataclass
class ParsedQuery:
    sql: str
    explanation: str


class NLSQLParser:
    def __init__(self, schema: Schema):
        self.s = schema
        self._adj: dict[str, list[tuple[str, str, str, str]]] = {}
        for t, c, rt, rc in schema.fks:
            self._adj.setdefault(t, []).append((t, c, rt, rc))
            self._adj.setdefault(rt, []).append((rt, rc, t, c))

    # ---------- helpers ----------
    def _match_column(self, word: str) -> tuple[str, str] | None:
        cands = [(t, c) for t, cols in self.s.tables.items() for c in cols]
        names = [c for _, c in cands]
        hit = difflib.get_close_matches(word, names, n=1, cutoff=0.82)
        if hit:
            for t, c in cands:
                if c == hit[0]:
                    return t, c
        # singular/plural relaxation
        for t, c in cands:
            if word.rstrip("s") == c.rstrip("s"):
                return t, c
        return None

    def _match_table(self, word: str) -> str | None:
        hit = difflib.get_close_matches(word.rstrip("s"),
                                        [t.rstrip("s") for t in self.s.tables], n=1, cutoff=0.8)
        if hit:
            for t in self.s.tables:
                if t.rstrip("s") == hit[0]:
                    return t
        return None

    def _join_path(self, start: str, goal: str) -> list[tuple[str, str, str, str]] | None:
        if start == goal:
            return []
        frontier, seen = [(start, [])], {start}
        while frontier:
            node, path = frontier.pop(0)
            for edge in self._adj.get(node, []):
                nxt = edge[2]
                if nxt in seen:
                    continue
                if nxt == goal:
                    return path + [edge]
                seen.add(nxt)
                frontier.append((nxt, path + [edge]))
        return None

    # ---------- main ----------
    def parse(self, question: str) -> ParsedQuery:
        q = question.lower().strip().rstrip("?")
        notes: list[str] = []

        # aggregate + metric
        agg, metric_expr, metric_table = None, None, None
        for word, (a, expr) in METRIC_SYNONYMS.items():
            if re.search(rf"\b{word}\b", q):
                agg, metric_expr = a, expr
                metric_table = self._table_containing(expr)
                notes.append(f"metric '{word}' -> {a}({expr})")
                break
        for word, a in AGG_WORDS.items():
            if word in q:
                agg = agg or a
                if a != "COUNT" and metric_expr is None:
                    m = re.search(rf"(?:{word})\s+(?:of\s+)?([a-z_ ]+?)(?:\s+(?:by|per|for|in)\b|$)", q)
                    if m:
                        col = self._match_column(m.group(1).strip().replace(" ", "_"))
                        if col:
                            metric_table, metric_expr = col[0], col[1]
                            notes.append(f"aggregate column -> {col[0]}.{col[1]}")
                break

        # group-by
        group_col: tuple[str, str] | None = None
        gm = re.search(r"\b(?:by|per)\s+([a-z_]+)", q)
        monthly = bool(re.search(r"\bmonthly\b|\bper month\b|\bby month\b", q))
        if gm and not monthly:
            group_col = self._match_column(gm.group(1))
            if group_col:
                notes.append(f"group by -> {group_col[0]}.{group_col[1]}")

        # top-N
        topn = None
        tm = re.search(r"\btop\s+(\d+)\s+([a-z_]+)", q)
        if tm:
            topn = int(tm.group(1))
            ent = self._match_table(tm.group(2)) or (self._match_column(tm.group(2)) or (None,))[0]
            if ent:
                name_col = self._name_column(ent)
                group_col = (ent, name_col)
                notes.append(f"top {topn} {ent} by name column '{name_col}'")

        # filters from value index
        filters: list[tuple[str, str, str]] = []
        for value, locs in self.s.values.items():
            if re.search(rf"\b{re.escape(value)}\b", q):
                t, c = locs[0]
                filters.append((t, c, value))
                notes.append(f"filter -> {t}.{c} = '{value}'")
        ym = re.search(r"\b(20\d\d)\b", q)
        year_filter = ym.group(1) if ym else None

        # base table
        base = metric_table
        if base is None and group_col:
            base = group_col[0]
        if base is None:
            for t in self.s.tables:
                if self._match_table_word(q, t):
                    base = t
                    break
        base = base or next(iter(self.s.tables))

        # entity count default
        if agg is None and re.search(r"\bhow many\b|\bcount\b|\bnumber of\b", q):
            agg = "COUNT"
        if agg == "COUNT" and metric_expr is None:
            counted = None
            for t in self.s.tables:
                if self._match_table_word(q, t):
                    counted = t
                    break
            base = counted or base
            metric_expr, metric_table = "*", base
        if agg is None:
            agg, metric_expr = agg or "COUNT", metric_expr or "*"
            metric_table = metric_table or base

        # assemble joins
        anchor = metric_table or base
        tables_needed = {anchor, base}
        if group_col:
            tables_needed.add(group_col[0])
        for t, _, _ in filters:
            tables_needed.add(t)
        date_table = None
        if monthly or year_filter:
            date_table = self._nearest_date_table(anchor)
            if date_table:
                tables_needed.add(date_table)
        join_sql, joined = self._build_joins(anchor, tables_needed)

        select, group_sql, order_sql = [], "", ""
        label = None
        if group_col:
            label = f'"{group_col[0]}"."{group_col[1]}"'
            select.append(f"{label} AS {group_col[1]}")
        if monthly and date_table:
            dcol = self._date_column(date_table)
            label = f'strftime(\'%Y-%m\', "{date_table}"."{dcol}")'
            select.append(f"{label} AS month")
            notes.append(f"monthly trend on {date_table}.{dcol}")
        metric_sql = f"{agg}({metric_expr})" if metric_expr != "*" else "COUNT(*)"
        select.append(f"{metric_sql} AS value")
        if label:
            group_sql = f" GROUP BY {label}"
            order_sql = " ORDER BY month" if monthly else " ORDER BY value DESC"
        where = []
        for t, c, v in filters:
            where.append(f'LOWER("{t}"."{c}") = \'{v}\'')
        if year_filter and date_table:
            where.append(f'strftime(\'%Y\', "{date_table}"."{self._date_column(date_table)}") '
                         f"= '{year_filter}'")
            notes.append(f"year filter {year_filter}")
        where_sql = (" WHERE " + " AND ".join(where)) if where else ""
        limit_sql = f" LIMIT {topn}" if topn else (" LIMIT 50" if label else "")
        sql = (f'SELECT {", ".join(select)} FROM "{anchor}"{join_sql}{where_sql}'
               f"{group_sql}{order_sql}{limit_sql}")
        return ParsedQuery(sql, "; ".join(notes) or "default count query")

    # ---------- schema utilities ----------
    def _table_containing(self, expr: str) -> str | None:
        cols = re.findall(r"[a-z_]+", expr)
        for t, tcols in self.s.tables.items():
            if all(c in tcols for c in cols):
                return t
        return None

    def _match_table_word(self, q: str, table: str) -> bool:
        return bool(re.search(rf"\b{table.rstrip('s')}s?\b", q))

    def _name_column(self, table: str) -> str:
        for cand in ("name", "title", "label"):
            if cand in self.s.tables.get(table, []):
                return cand
        return self.s.tables[table][1] if len(self.s.tables[table]) > 1 else self.s.tables[table][0]

    def _nearest_date_table(self, anchor: str) -> str | None:
        """Table with a date column, closest to the anchor over the FK graph."""
        best, best_len = None, 10 ** 9
        for t in self.s.tables:
            if not self._date_column(t):
                continue
            path = self._join_path(anchor, t)
            if path is not None and len(path) < best_len:
                best, best_len = t, len(path)
        return best

    def _date_column(self, table: str) -> str | None:
        for c in self.s.tables.get(table, []):
            if "date" in c or c.endswith("_at") or c == "ts":
                return c
        return None

    def _build_joins(self, anchor: str, needed: set[str]) -> tuple[str, set[str]]:
        joined = {anchor}
        sql = ""
        for target in sorted(needed - {anchor}):
            path = self._join_path(anchor, target)
            if path is None:
                continue
            for t, c, rt, rc in path:
                if rt in joined:
                    continue
                sql += f' JOIN "{rt}" ON "{t}"."{c}" = "{rt}"."{rc}"'
                joined.add(rt)
        return sql, joined
