"""Executive Dashboard — Questions 1–5."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.linear_model import LinearRegression
import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.utils import inject_theme, show_chart, apply_filters, inr, kpi_row, load_customers, load_products, load_transactions, yoy_delta
from src.config import AMAZON_NAVY, AMAZON_ORANGE, PALETTE

st.set_page_config(page_title="Executive Dashboard", layout="wide")
inject_theme()
st.title("Executive Dashboard")
st.caption("Questions 1–5 · C-level KPIs, performance vs target, strategy, finance, growth")

tx = apply_filters(load_transactions())
customers = load_customers()
products = load_products()
if tx.empty:
    st.stop()

latest = int(tx["order_year"].max())
prev = latest - 1
by_year = tx.groupby("order_year").agg(
    revenue=("final_amount_inr", "sum"),
    orders=("transaction_id", "count"),
    customers=("customer_id", "nunique"),
    aov=("final_amount_inr", "mean"),
)

# --- Q1 Executive summary ---
st.header("Q1 · Executive summary")
kpi_row(
    [
        ("Total revenue", inr(float(tx["final_amount_inr"].sum())), yoy_delta(by_year["revenue"].get(latest, 0), by_year["revenue"].get(prev, 0))),
        ("Growth rate (latest YoY)", yoy_delta(by_year["revenue"].get(latest, 0), by_year["revenue"].get(prev, 0)) or "n/a", None),
        ("Active customers", f"{tx['customer_id'].nunique():,}", yoy_delta(by_year["customers"].get(latest, 0), by_year["customers"].get(prev, 0))),
        ("AOV", inr(float(tx["final_amount_inr"].mean()), 0), yoy_delta(by_year["aov"].get(latest, 0), by_year["aov"].get(prev, 0))),
        ("Top subcategory", tx.groupby("subcategory")["final_amount_inr"].sum().idxmax(), None),
    ]
)
c1, c2 = st.columns(2)
y = by_year.reset_index()
y["yoy"] = y["revenue"].pct_change()
with c1:
    fig = px.bar(y, x="order_year", y="revenue", title="Revenue vs prior years", color_discrete_sequence=[AMAZON_ORANGE])
    show_chart(fig)
with c2:
    top = tx.groupby("subcategory", as_index=False)["final_amount_inr"].sum().sort_values("final_amount_inr", ascending=False)
    fig = px.bar(top, x="subcategory", y="final_amount_inr", title="Top performing subcategories", color_discrete_sequence=[AMAZON_NAVY])
    show_chart(fig)

# --- Q2 Real-time monitor ---
st.header("Q2 · Business performance monitor")
latest_month = tx["order_date"].max().to_period("M")
this_month = tx[tx["order_date"].dt.to_period("M") == latest_month]
same_month_ly = tx[tx["order_date"].dt.to_period("M") == (latest_month - 12)]
target = float(same_month_ly["final_amount_inr"].sum()) * 1.10
actual = float(this_month["final_amount_inr"].sum())
days_in_month = latest_month.days_in_month
day_num = tx["order_date"].max().day
run_rate = actual / max(day_num, 1) * days_in_month
new_this = this_month["customer_id"].nunique()
alert = actual < 0.9 * target if target else False
k1, k2, k3, k4 = st.columns(4)
k1.metric(f"Month {latest_month} revenue", inr(actual), yoy_delta(actual, float(same_month_ly["final_amount_inr"].sum())))
k2.metric("Target (LY +10%)", inr(target), f"{(actual / target - 1) * 100:+.1f}%" if target else None)
k3.metric("Revenue run-rate", inr(run_rate))
k4.metric("Customers active this month", f"{new_this:,}")
if alert:
    st.error("Alert: current month is more than 10% below the year-ago +10% target.")
elif target and actual >= target:
    st.success("On or above the current-month target.")
else:
    st.warning("Within 10% of target — watch daily run-rate.")

# --- Q3 Strategic overview ---
st.header("Q3 · Strategic overview")
g1, g2, g3 = st.columns(3)
with g1:
    tier = tx.groupby("customer_tier", as_index=False)["final_amount_inr"].sum()
    fig = px.pie(tier, names="customer_tier", values="final_amount_inr", title="Revenue by city tier", hole=0.4)
    show_chart(fig)
with g2:
    brand_share = tx.groupby("brand")["final_amount_inr"].sum().nlargest(6).reset_index()
    fig = px.bar(brand_share, x="brand", y="final_amount_inr", title="Competitive brand share (top 6)", color_discrete_sequence=[AMAZON_ORANGE])
    show_chart(fig)
with g3:
    geo = tx.groupby("customer_state", as_index=False)["final_amount_inr"].sum().nlargest(10, "final_amount_inr")
    fig = px.bar(geo, x="customer_state", y="final_amount_inr", title="Geographic concentration", color_discrete_sequence=[AMAZON_NAVY])
    show_chart(fig)
st.caption("Market share here is internal brand/category mix — the files contain no competitor GMV.")

# --- Q4 Financial performance ---
st.header("Q4 · Financial performance")
tx = tx.copy()
tx["estimated_cogs"] = tx["discounted_price_inr"] * tx["quantity"] * 0.72
tx["gross_profit"] = tx["final_amount_inr"] - tx["estimated_cogs"] - tx["delivery_charges"]
fin = tx.groupby("subcategory").agg(revenue=("final_amount_inr", "sum"), gross_profit=("gross_profit", "sum"), delivery=("delivery_charges", "sum"))
fin["margin_pct"] = fin["gross_profit"] / fin["revenue"] * 100
c1, c2 = st.columns(2)
with c1:
    fig = px.bar(fin.reset_index(), x="subcategory", y="revenue", title="Revenue by subcategory", color_discrete_sequence=[AMAZON_ORANGE])
    show_chart(fig)
with c2:
    fig = px.bar(fin.reset_index(), x="subcategory", y="margin_pct", title="Estimated gross margin % (COGS proxy 72% of discounted price)", color_discrete_sequence=[AMAZON_NAVY])
    show_chart(fig)
monthly = tx.groupby(tx["order_date"].dt.to_period("M"))["final_amount_inr"].sum()
monthly.index = monthly.index.to_timestamp()
X = np.arange(len(monthly)).reshape(-1, 1)
model = LinearRegression().fit(X, monthly.values)
future_x = np.arange(len(monthly) + 6).reshape(-1, 1)
pred = model.predict(future_x)
fig = go.Figure()
fig.add_trace(go.Scatter(x=monthly.index, y=monthly.values, name="Actual", line=dict(color=AMAZON_ORANGE)))
future_idx = pd.date_range(monthly.index.min(), periods=len(pred), freq="MS")
fig.add_trace(go.Scatter(x=future_idx, y=pred, name="Linear forecast", line=dict(color=AMAZON_NAVY, dash="dash")))
fig.update_layout(title="Revenue forecast (linear baseline, next 6 months)")
show_chart(fig)
st.caption("The files have no cost ledger. Margin uses a documented 72% COGS proxy so the chart is directional, not statutory P&L.")

# --- Q5 Growth analytics ---
st.header("Q5 · Growth analytics")
acq = customers.groupby("acquisition_year").size().rename("new_customers")
active = tx.groupby("order_year")["customer_id"].nunique().rename("active_customers")
growth = pd.concat([acq, active], axis=1).fillna(0)
growth["portfolio_skus"] = tx.groupby("order_year")["product_id"].nunique()
g1, g2 = st.columns(2)
with g1:
    fig = px.line(growth.reset_index(), x="index", y=["new_customers", "active_customers"], title="Customer growth vs active base", markers=True)
    show_chart(fig)
with g2:
    fig = px.bar(growth.reset_index(), x="index", y="portfolio_skus", title="Active product portfolio by year", color_discrete_sequence=[AMAZON_ORANGE])
    show_chart(fig)
metro_share = tx.groupby("order_year")["customer_tier"].apply(lambda s: (s == "Metro").mean())
st.line_chart(metro_share.rename("Metro order share"))
