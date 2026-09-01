"""SQLite schema, load, indexes, and dashboard queries."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.config import CLEANED_DIR, DB_PATH, SQL_DIR

SCHEMA_SQL = """
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS time_dimension;

CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT,
    category TEXT,
    subcategory TEXT,
    brand TEXT,
    base_price_2015 REAL,
    weight_kg REAL,
    rating REAL,
    is_prime_eligible INTEGER,
    launch_year INTEGER,
    model TEXT,
    units_sold INTEGER,
    orders INTEGER,
    revenue REAL,
    avg_discount REAL,
    avg_customer_rating REAL,
    return_rate REAL,
    first_sold TEXT,
    last_sold TEXT
);

CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    customer_city TEXT,
    customer_state TEXT,
    customer_tier TEXT,
    customer_spending_tier TEXT,
    customer_age_group TEXT,
    is_prime_member INTEGER,
    first_order_date TEXT,
    last_order_date TEXT,
    frequency INTEGER,
    monetary REAL,
    units INTEGER,
    avg_order_value REAL,
    avg_rating REAL,
    return_rate REAL,
    recency_days INTEGER,
    tenure_days INTEGER,
    acquisition_year INTEGER,
    r_score INTEGER,
    f_score INTEGER,
    m_score INTEGER,
    rfm_segment TEXT,
    rfm_action TEXT,
    clv REAL
);

CREATE TABLE time_dimension (
    date TEXT PRIMARY KEY,
    year INTEGER,
    quarter INTEGER,
    month INTEGER,
    month_name TEXT,
    week INTEGER,
    day INTEGER,
    day_of_week INTEGER,
    day_name TEXT,
    is_weekend INTEGER,
    year_month TEXT,
    year_quarter TEXT,
    festival_name TEXT,
    is_festival INTEGER
);

CREATE TABLE transactions (
    transaction_id TEXT PRIMARY KEY,
    order_date TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    product_name TEXT,
    category TEXT,
    subcategory TEXT,
    brand TEXT,
    original_price_inr REAL,
    discount_percent REAL,
    discounted_price_inr REAL,
    quantity INTEGER,
    subtotal_inr REAL,
    delivery_charges REAL,
    final_amount_inr REAL,
    customer_city TEXT,
    customer_state TEXT,
    customer_tier TEXT,
    customer_spending_tier TEXT,
    customer_age_group TEXT,
    payment_method TEXT,
    payment_method_group TEXT,
    delivery_days INTEGER,
    delivery_type TEXT,
    is_prime_member INTEGER,
    is_prime_eligible INTEGER,
    is_festival_sale INTEGER,
    festival_name TEXT,
    customer_rating REAL,
    customer_rating_imputed REAL,
    return_status TEXT,
    order_month INTEGER,
    order_year INTEGER,
    order_quarter INTEGER,
    order_day INTEGER,
    product_weight_kg REAL,
    product_rating REAL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (order_date) REFERENCES time_dimension(date)
);

CREATE INDEX idx_txn_date ON transactions(order_date);
CREATE INDEX idx_txn_customer ON transactions(customer_id);
CREATE INDEX idx_txn_product ON transactions(product_id);
CREATE INDEX idx_txn_year ON transactions(order_year);
CREATE INDEX idx_txn_category ON transactions(category);
CREATE INDEX idx_txn_subcategory ON transactions(subcategory);
CREATE INDEX idx_txn_city ON transactions(customer_city);
CREATE INDEX idx_txn_state ON transactions(customer_state);
CREATE INDEX idx_txn_payment ON transactions(payment_method);
CREATE INDEX idx_txn_prime ON transactions(is_prime_member);
CREATE INDEX idx_txn_festival ON transactions(is_festival_sale);
CREATE INDEX idx_txn_brand ON transactions(brand);
CREATE INDEX idx_cust_segment ON customers(rfm_segment);
CREATE INDEX idx_cust_city ON customers(customer_city);
CREATE INDEX idx_prod_brand ON products(brand);
CREATE INDEX idx_prod_subcat ON products(subcategory);
"""

DASHBOARD_QUERIES = """
-- KPI: yearly revenue and orders
SELECT order_year,
       SUM(final_amount_inr) AS revenue,
       COUNT(*) AS orders,
       COUNT(DISTINCT customer_id) AS active_customers,
       AVG(final_amount_inr) AS aov
FROM transactions
GROUP BY order_year
ORDER BY order_year;

-- Category (subcategory) contribution
SELECT subcategory,
       SUM(final_amount_inr) AS revenue,
       SUM(quantity) AS units,
       COUNT(DISTINCT customer_id) AS customers
FROM transactions
GROUP BY subcategory
ORDER BY revenue DESC;

-- Geographic revenue
SELECT customer_state, customer_tier,
       SUM(final_amount_inr) AS revenue,
       COUNT(*) AS orders
FROM transactions
GROUP BY customer_state, customer_tier
ORDER BY revenue DESC;

-- Prime vs non-Prime
SELECT is_prime_member,
       COUNT(*) AS orders,
       SUM(final_amount_inr) AS revenue,
       AVG(final_amount_inr) AS aov,
       AVG(delivery_days) AS avg_delivery_days
FROM transactions
GROUP BY is_prime_member;

-- RFM segment value
SELECT rfm_segment,
       COUNT(*) AS customers,
       SUM(monetary) AS revenue,
       AVG(clv) AS avg_clv
FROM customers
GROUP BY rfm_segment
ORDER BY revenue DESC;

-- Multi-table: brand x year
SELECT t.order_year, t.brand,
       SUM(t.final_amount_inr) AS revenue,
       SUM(t.quantity) AS units
FROM transactions t
JOIN products p ON t.product_id = p.product_id
GROUP BY t.order_year, t.brand
ORDER BY t.order_year, revenue DESC;
"""


def _prepare_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].dt.strftime("%Y-%m-%d")
        elif pd.api.types.is_bool_dtype(out[col]):
            out[col] = out[col].astype(int)
    return out


def load_database(
    tx: pd.DataFrame | None = None,
    customers: pd.DataFrame | None = None,
    products: pd.DataFrame | None = None,
    time_dim: pd.DataFrame | None = None,
) -> Path:
    SQL_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    (SQL_DIR / "schema.sql").write_text(SCHEMA_SQL.strip() + "\n", encoding="utf-8")
    (SQL_DIR / "dashboard_queries.sql").write_text(DASHBOARD_QUERIES.strip() + "\n", encoding="utf-8")

    if tx is None:
        tx = pd.read_parquet(CLEANED_DIR / "transactions_cleaned.parquet")
    if customers is None:
        customers = pd.read_parquet(CLEANED_DIR / "customers.parquet")
    if products is None:
        products = pd.read_parquet(CLEANED_DIR / "products.parquet")
    if time_dim is None:
        time_dim = pd.read_parquet(CLEANED_DIR / "time_dimension.parquet")

    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA_SQL)
        _prepare_frame(products).to_sql("products", conn, if_exists="append", index=False)
        _prepare_frame(customers).to_sql("customers", conn, if_exists="append", index=False)
        _prepare_frame(time_dim).to_sql("time_dimension", conn, if_exists="append", index=False)
        _prepare_frame(tx).to_sql("transactions", conn, if_exists="append", index=False)
        conn.execute("ANALYZE")
        conn.commit()
        counts = {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ["transactions", "customers", "products", "time_dimension"]
        }
        print("SQLite loaded:", counts, "→", DB_PATH)
    finally:
        conn.close()
    return DB_PATH


def fetch_df(sql: str, params: tuple | list | None = None) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


if __name__ == "__main__":
    load_database()
