"""SQL Analytics Agent — interactive REPL shell.

Run with:
    python -m sqa              # opens REPL, auto-creates demo DB
    python -m sqa --db PATH    # opens REPL against an existing SQLite file
    python -m sqa --demo       # non-interactive: run the demo battery and exit

Inside the REPL:
    ask  <question>         natural-language question against the loaded DB
    sql  <SELECT ...>       run a guarded read-only SQL statement
    schema                  describe tables, columns, and foreign keys
    demo                    run the built-in NL question battery
    help / ?                list commands
    quit / q / exit         leave
"""
from __future__ import annotations

import argparse
import cmd
import sys
from pathlib import Path

from .agent import SQLAnalyticsAgent, analytics_report
from .db import create_demo_db

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output"

DEMO_QUESTIONS = [
    "total revenue",
    "top 5 products by revenue",
    "revenue by country",
    "how many customers per segment",
    "average revenue by channel",
    "monthly revenue in 2024",
    "how many orders were cancelled",
    "revenue in Germany",
]

BANNER = """\
╔═══════════════════════════════════════════════════╗
║   SQL Analytics Agent  — interactive REPL shell  ║
║   type  help  for commands,  quit  to exit        ║
╚═══════════════════════════════════════════════════╝
"""


class SQLShell(cmd.Cmd):
    """cmd.Cmd REPL that wraps SQLAnalyticsAgent."""

    intro = BANNER
    prompt = "sqa> "

    def __init__(self, agent: SQLAnalyticsAgent) -> None:
        super().__init__()
        self._agent = agent

    # ── commands ──────────────────────────────────────────────────────────────

    def do_ask(self, line: str) -> None:
        """ask <question>   — answer a natural-language question against the DB."""
        if not line.strip():
            print("Usage: ask <natural-language question>")
            return
        try:
            print(self._agent.ask(line.strip()).render())
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}")

    def do_sql(self, line: str) -> None:
        """sql <SELECT ...>  — run a guarded read-only SQL query."""
        if not line.strip():
            print("Usage: sql <SELECT statement>")
            return
        try:
            cols, rows = self._agent.execute(line.strip())
            print(" | ".join(cols))
            for r in rows[:30]:
                print(" | ".join(str(v) for v in r))
            if len(rows) > 30:
                print(f"  … {len(rows) - 30} more rows")
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}")

    def do_schema(self, _line: str) -> None:
        """schema  — describe tables, columns, and foreign keys."""
        print(self._agent.schema.describe())

    def do_demo(self, _line: str) -> None:
        """demo  — run the built-in NL question battery."""
        print(f"Running {len(DEMO_QUESTIONS)} demo questions …\n")
        for q in DEMO_QUESTIONS:
            print(self._agent.ask(q).render())
            print("-" * 72)
        report_p = OUT / "analytics_report.md"
        OUT.mkdir(exist_ok=True)
        analytics_report(self._agent, DEMO_QUESTIONS, report_p)
        print(f"\nReport → {report_p}")

    def do_quit(self, _line: str) -> bool:
        """quit / q / exit  — leave the REPL."""
        print("Goodbye.")
        return True

    do_q = do_exit = do_quit

    def default(self, line: str) -> None:
        print(f"Unknown command: {line!r}. Type 'help' for a list of commands.")

    def emptyline(self) -> None:
        pass  # do nothing on blank input


def _build_agent(db_path: Path | None, use_llm: bool) -> SQLAnalyticsAgent:
    if db_path is None:
        OUT.mkdir(exist_ok=True)
        db_path = OUT / "retail.db"
        if not db_path.exists():
            print(f"Creating demo DB → {db_path}")
            create_demo_db(db_path)
    return SQLAnalyticsAgent(db_path, use_llm=use_llm)


def main() -> None:
    p = argparse.ArgumentParser(description="SQL Analytics Agent REPL")
    p.add_argument("--db", type=Path, help="path to an SQLite database file")
    p.add_argument("--no-llm", action="store_true", help="force offline parser mode")
    p.add_argument("--demo", action="store_true", help="run demo battery and exit (non-interactive)")
    args = p.parse_args()

    agent = _build_agent(args.db, use_llm=not args.no_llm)
    shell = SQLShell(agent)

    if args.demo:
        # Non-interactive: run the demo battery and exit without the REPL loop
        shell.onecmd("demo")
        sys.exit(0)

    try:
        shell.cmdloop()
    except KeyboardInterrupt:
        print("\nInterrupted. Goodbye.")


if __name__ == "__main__":
    main()
