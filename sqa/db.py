"""SQLite schema introspection, value index, and a seeded demo retail database."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class Schema:
    tables: dict[str, list[str]] = field(default_factory=dict)          # table -> columns
    types: dict[tuple[str, str], str] = field(default_factory=dict)     # (table, col) -> type
    fks: list[tuple[str, str, str, str]] = field(default_factory=list)  # (table, col, ref_table, ref_col)
    values: dict[str, list[tuple[str, str]]] = field(default_factory=dict)  # lower value -> [(table, col)]

    def describe(self) -> str:
        out = []
        for t, cols in self.tables.items():
            typed = ", ".join(f"{c} {self.types.get((t, c), '')}".strip() for c in cols)
            out.append(f"TABLE {t}({typed})")
        for t, c, rt, rc in self.fks:
            out.append(f"FK {t}.{c} -> {rt}.{rc}")
        return "\n".join(out)


def introspect(conn: sqlite3.Connection, value_index_max_card: int = 60) -> Schema:
    s = Schema()
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    for t in tables:
        cols = conn.execute(f'PRAGMA table_info("{t}")').fetchall()
        s.tables[t] = [c[1] for c in cols]
        for c in cols:
            s.types[(t, c[1])] = (c[2] or "").upper()
        for fk in conn.execute(f'PRAGMA foreign_key_list("{t}")').fetchall():
            s.fks.append((t, fk[3], fk[2], fk[4]))
        # value index over low-cardinality text columns for filter matching
        for c in cols:
            if "CHAR" in (c[2] or "").upper() or "TEXT" in (c[2] or "").upper():
                distinct = conn.execute(
                    f'SELECT DISTINCT "{c[1]}" FROM "{t}" LIMIT {value_index_max_card + 1}').fetchall()
                if 0 < len(distinct) <= value_index_max_card:
                    for (v,) in distinct:
                        if isinstance(v, str) and v:
                            s.values.setdefault(v.lower(), []).append((t, c[1]))
    return s


COUNTRIES = ["USA", "Germany", "UK", "France", "Canada", "Japan", "Brazil", "India"]
SEGMENTS = ["consumer", "corporate", "small business"]
CHANNELS = ["web", "mobile app", "phone", "retail store"]
STATUSES = ["completed", "shipped", "cancelled", "returned"]
PRODUCTS = [
    ("Laptop Pro 15", "electronics", 1450.0), ("Wireless Mouse", "electronics", 35.0),
    ("Mechanical Keyboard", "electronics", 120.0), ("4K Monitor", "electronics", 420.0),
    ("Office Chair", "furniture", 310.0), ("Standing Desk", "furniture", 540.0),
    ("Desk Lamp", "furniture", 45.0), ("Notebook Set", "stationery", 12.0),
    ("Fountain Pen", "stationery", 58.0), ("Espresso Machine", "appliances", 260.0),
    ("Air Purifier", "appliances", 180.0), ("Noise-Canceling Headphones", "electronics", 330.0),
]


def create_demo_db(path: str | Path, seed: int = 42, n_customers: int = 400,
                   n_orders: int = 2500) -> None:
    rng = np.random.default_rng(seed)
    p = Path(path)
    if p.exists():
        p.unlink()
    conn = sqlite3.connect(p)
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE customers(customer_id INTEGER PRIMARY KEY, name TEXT, country TEXT,
        city TEXT, segment TEXT, signup_date TEXT);
    CREATE TABLE products(product_id INTEGER PRIMARY KEY, name TEXT, category TEXT, price REAL);
    CREATE TABLE orders(order_id INTEGER PRIMARY KEY, customer_id INTEGER, order_date TEXT,
        status TEXT, channel TEXT,
        FOREIGN KEY(customer_id) REFERENCES customers(customer_id));
    CREATE TABLE order_items(item_id INTEGER PRIMARY KEY, order_id INTEGER, product_id INTEGER,
        quantity INTEGER, unit_price REAL,
        FOREIGN KEY(order_id) REFERENCES orders(order_id),
        FOREIGN KEY(product_id) REFERENCES products(product_id));
    """)
    first = ["Alex", "Sam", "Jordan", "Taylor", "Morgan", "Casey", "Riya", "Omar", "Lena", "Kai"]
    last = ["Chen", "Patel", "Garcia", "Kim", "Novak", "Silva", "Haddad", "Okafor", "Weber", "Ito"]
    for cid in range(1, n_customers + 1):
        cur.execute("INSERT INTO customers VALUES (?,?,?,?,?,?)",
                    (cid, f"{rng.choice(first)} {rng.choice(last)}", str(rng.choice(COUNTRIES)),
                     f"City{rng.integers(1, 40)}", str(rng.choice(SEGMENTS, p=[0.55, 0.25, 0.2])),
                     f"202{rng.integers(2, 5)}-{rng.integers(1, 13):02d}-{rng.integers(1, 28):02d}"))
    for pid, (name, cat, price) in enumerate(PRODUCTS, 1):
        cur.execute("INSERT INTO products VALUES (?,?,?,?)", (pid, name, cat, price))
    item_id = 1
    for oid in range(1, n_orders + 1):
        cid = int(rng.integers(1, n_customers + 1))
        y, m, d = 2024 + int(rng.random() < 0.45), int(rng.integers(1, 13)), int(rng.integers(1, 28))
        cur.execute("INSERT INTO orders VALUES (?,?,?,?,?)",
                    (oid, cid, f"{y}-{m:02d}-{d:02d}",
                     str(rng.choice(STATUSES, p=[0.72, 0.15, 0.08, 0.05])),
                     str(rng.choice(CHANNELS, p=[0.45, 0.3, 0.1, 0.15]))))
        for _ in range(int(rng.integers(1, 5))):
            pid = int(rng.integers(1, len(PRODUCTS) + 1))
            qty = int(rng.integers(1, 4))
            price = PRODUCTS[pid - 1][2] * float(rng.uniform(0.9, 1.05))
            cur.execute("INSERT INTO order_items VALUES (?,?,?,?,?)",
                        (item_id, oid, pid, qty, round(price, 2)))
            item_id += 1
    conn.commit()
    conn.close()
