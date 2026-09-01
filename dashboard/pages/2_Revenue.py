"""Revenue Analytics — Questions 6–10."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.utils import inject_theme, show_chart, apply_filters, inr, load_transactions
from src.config import AMAZON_NAVY, AMAZON_ORANGE, CITY_COORDS, PALETTE

st.set_page_config(page_title="Revenue Analytics", layout="wide")
inject_theme()
st.title("Revenue Analytics")
st.caption("Questions 6–10 · trends, categories, geography, festivals, price")

tx = apply_filters(load_transactions())
if tx.empty:
    st.stop()

grain = st.radio("Time grain", ["Monthly", "Quarterly", "Yearly"], horizontal=True)
if grain == "Yearly":
    ts = tx.groupby("order_year", as_index=False)["final_amount_inr"].sum().rename(columns={"order_year": "period"})
elif grain == "Quarterly":
    tx["period"] = tx["order_year"].astype(str) + "-Q" + tx["order_quarter"].astype(str)
    ts = tx.groupby("period", as_index=False)["final_amount_inr"].sum()
else:
    tx["period"] = tx["order_date"].dt.to_period("M").astype(str)
    ts = tx.groupby("period", as_index=False)["final_amount_inr"].sum()
ts["growth"] = ts["final_amount_inr"].pct_change() * 100

st.header("Q6 · Revenue trend analysis")
fig = px.line(ts, x="period", y="final_amount_inr", markers=True, title=f"{grain} revenue")
fig.update_traces(line_color=AMAZON_ORANGE)
show_chart(fig)
fig = px.bar(ts, x="period", y="growth", title="Period growth rate (%)", color_discrete_sequence=[AMAZON_NAVY])
show_chart(fig)

st.header("Q7 · Category performance")
cat = tx.groupby(["order_year", "subcategory"], as_index=False)["final_amount_inr"].sum()
c1, c2 = st.columns(2)
with c1:
    fig = px.area(cat, x="order_year", y="final_amount_inr", color="subcategory", title="Revenue by subcategory over time")
    show_chart(fig)
with c2:
    latest = cat[cat["order_year"] == cat["order_year"].max()]
    fig = px.pie(latest, names="subcategory", values="final_amount_inr", title="Latest-year market share")
    show_chart(fig)
drill = st.selectbox("Drill into subcategory", sorted(tx["subcategory"].unique()))
brand = tx[tx["subcategory"] == drill].groupby("brand", as_index=False)["final_amount_inr"].sum().nlargest(12, "final_amount_inr")
show_chart(px.bar(brand, x="brand", y="final_amount_inr", title=f"{drill} · brand drill-down", color_discrete_sequence=[AMAZON_ORANGE]))

st.header("Q8 · Geographic revenue")
state = tx.groupby(["customer_state", "customer_tier"], as_index=False).agg(revenue=("final_amount_inr", "sum"), orders=("transaction_id", "count"))
fig = px.bar(state, x="customer_state", y="revenue", color="customer_tier", title="State × tier revenue")
show_chart(fig)
city = tx.groupby("customer_city", as_index=False)["final_amount_inr"].sum()
city["lat"] = city["customer_city"].map(lambda c: CITY_COORDS.get(c, (None, None))[0])
city["lon"] = city["customer_city"].map(lambda c: CITY_COORDS.get(c, (None, None))[1])
fig = px.scatter_geo(city.dropna(), lat="lat", lon="lon", size="final_amount_inr", hover_name="customer_city", title="City revenue density", scope="asia")
fig.update_geos(center=dict(lat=22, lon=79), projection_scale=4)
show_chart(fig)

st.header("Q9 · Festival sales")
fest = tx[tx["is_festival_sale"]].groupby("festival_name", as_index=False).agg(revenue=("final_amount_inr", "sum"), orders=("transaction_id", "count"), aov=("final_amount_inr", "mean"), avg_discount=("discount_percent", "mean"))
st.dataframe(fest.sort_values("revenue", ascending=False), width="stretch")
fest_month = tx.assign(year_month=tx["order_date"].dt.to_period("M").astype(str))
monthly = fest_month.groupby(["year_month", "is_festival_sale"], as_index=False)["final_amount_inr"].sum()
fig = px.bar(monthly, x="year_month", y="final_amount_inr", color="is_festival_sale", title="Festival vs non-festival revenue by month")
show_chart(fig)

st.header("Q10 · Price optimisation")
tx["disc_bin"] = pd.cut(tx["discount_percent"], bins=[-0.01, 0, 10, 20, 30, 50, 80], labels=["0%", "0-10", "10-20", "20-30", "30-50", "50+"])
elas = tx.groupby(["subcategory", "disc_bin"], as_index=False).agg(units=("quantity", "sum"), revenue=("final_amount_inr", "sum"), aov=("final_amount_inr", "mean"))
fig = px.bar(elas, x="disc_bin", y="units", color="subcategory", barmode="group", title="Units by discount band")
show_chart(fig)
prod = tx.groupby("product_id", as_index=False).agg(price=("discounted_price_inr", "median"), units=("quantity", "sum"), discount=("discount_percent", "mean"), subcategory=("subcategory", "first"))
fig = px.scatter(prod, x="price", y="units", color="subcategory", size="discount", log_x=True, log_y=True, title="Price vs demand (bubble = avg discount)")
show_chart(fig)
