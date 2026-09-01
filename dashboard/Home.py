"""Amazon India Sales Analytics — Streamlit entry point."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.utils import inject_theme, show_chart, apply_filters, inr, kpi_row, load_customers, load_transactions, yoy_delta
from src.config import AMAZON_NAVY, AMAZON_ORANGE

st.set_page_config(
    page_title="Amazon India | Decade of Sales Analytics",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_theme()

st.title("Amazon India: A Decade of Sales Analytics")
st.caption("Cleaned transactional warehouse · 2015–2025 · Streamlit BI layer over SQLite-ready parquet")

tx = apply_filters(load_transactions())
customers = load_customers()

if tx.empty:
    st.warning("No rows in the current filter. Widen the year, state, or subcategory selection.")
    st.stop()

latest_year = int(tx["order_year"].max())
prev_year = latest_year - 1
rev = tx.groupby("order_year")["final_amount_inr"].sum()
cust_n = tx.groupby("order_year")["customer_id"].nunique()
aov = tx.groupby("order_year")["final_amount_inr"].mean()

kpi_row(
    [
        ("Revenue in view", inr(float(tx["final_amount_inr"].sum())), yoy_delta(rev.get(latest_year, 0), rev.get(prev_year, 0))),
        ("Orders", f"{len(tx):,}", None),
        ("Active customers", f"{tx['customer_id'].nunique():,}", yoy_delta(cust_n.get(latest_year, 0), cust_n.get(prev_year, 0))),
        ("Average order value", inr(float(tx["final_amount_inr"].mean()), 0), yoy_delta(aov.get(latest_year, 0), aov.get(prev_year, 0))),
        ("Prime order share", f"{tx['is_prime_member'].mean() * 100:.1f}%", None),
    ]
)

left, right = st.columns((2, 1))
yearly = tx.groupby("order_year", as_index=False).agg(revenue=("final_amount_inr", "sum"), orders=("transaction_id", "count"))
with left:
    fig = px.line(yearly, x="order_year", y="revenue", markers=True, title="Revenue trajectory in the current filter")
    fig.update_traces(line_color=AMAZON_ORANGE)
    fig.update_layout(yaxis_title="INR", xaxis_title="Year")
    show_chart(fig)
with right:
    cats = tx.groupby("subcategory", as_index=False)["final_amount_inr"].sum().sort_values("final_amount_inr", ascending=False)
    fig = px.pie(cats, names="subcategory", values="final_amount_inr", title="Revenue mix", hole=0.45)
    show_chart(fig)

st.subheader("How to use this workspace")
st.markdown(
    """
Use the **sidebar filters** on every page. They slice the same cleaned warehouse.

| Page | Questions covered |
| --- | --- |
| Data Cleaning | Practice questions 1–10 (dates, prices, ratings, cities, booleans, categories, delivery, duplicates, outliers, payments) |
| EDA | Visualisation questions 1–20 with charts and verified numbers |
| Executive Dashboard | Dashboard 1–5 |
| Revenue Analytics | Dashboard 6–10 |
| Customer Analytics | Dashboard 11–15 |
| Product & Inventory | Dashboard 16–20 |
| Operations & Logistics | Dashboard 21–25 |
| Advanced Analytics | Dashboard 26–30 |

Data pipeline: raw CSVs → `src/cleaning.py` (10 cleaning challenges) → parquet → SQLite (`data/amazon_india_analytics.db`) → this app.
"""
)
st.info(f"SQLite warehouse path: `{ROOT / 'data' / 'amazon_india_analytics.db'}`  ·  Snapshot customers: {len(customers):,}")
