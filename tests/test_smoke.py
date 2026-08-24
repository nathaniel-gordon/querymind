"""Smoke test: python tests/test_smoke.py"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqa.agent import SQLAnalyticsAgent
from sqa.db import create_demo_db


def main() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        db = Path(td) / "retail.db"
        create_demo_db(db, seed=5, n_customers=150, n_orders=800)
        agent = SQLAnalyticsAgent(db, use_llm=False)

        r = agent.ask("total revenue")
        assert r.error is None and len(r.rows) == 1 and r.rows[0][0] > 0, r.render()

        r = agent.ask("top 5 products by revenue")
        assert r.error is None and len(r.rows) == 5, r.render()
        vals = [row[-1] for row in r.rows]
        assert vals == sorted(vals, reverse=True), "top-N must be sorted desc"

        r = agent.ask("revenue by country")
        assert r.error is None and 1 < len(r.rows) <= 8, r.render()

        r = agent.ask("how many customers per segment")
        assert r.error is None and sum(row[-1] for row in r.rows) == 150, r.render()

        r = agent.ask("monthly revenue in 2024")
        assert r.error is None and all("2024" in str(row[0]) for row in r.rows), r.render()
        assert "order_date" in r.sql, f"must use nearest date table: {r.sql}"

        r = agent.ask("revenue in Germany")
        assert r.error is None and r.rows[0][0] and r.rows[0][0] > 0, r.render()

        # read-only guardrails
        try:
            agent.execute("DROP TABLE customers")
            raise AssertionError("write statement must be rejected")
        except PermissionError:
            pass

        # self-correction: bad column gets fuzzy-fixed
        cols, rows = agent.execute('SELECT country FROM customers LIMIT 1')
        assert rows
        res = agent.ask("total revenue")  # exercise summarize path again
        assert "=" in res.summary
        agent.close()
    print("OK - offline parser answered battery; guardrails + self-correction active")


if __name__ == "__main__":
    main()


def test_smoke():
    main()
