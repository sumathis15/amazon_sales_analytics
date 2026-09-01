"""Operations & Logistics — Questions 21–25."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.utils import apply_filters, inr, load_transactions
from src.config import AMAZON_NAVY, AMAZON_ORANGE

st.set_page_config(page_title="Operations", layout="wide")
st.title("Operations & Logistics")
st.caption("Questions 21–25 · delivery, payments, returns, service, supply chain")

tx = apply_filters(load_transactions())
if tx.empty:
    st.stop()

sla = {"Same Day": 1, "Express": 2, "Standard": 5}
tx = tx.copy()
tx["on_time"] = tx["delivery_days"] <= tx["delivery_type"].map(sla)

st.header("Q21 · Delivery performance")
c1, c2, c3 = st.columns(3)
c1.metric("Avg delivery days", f"{tx['delivery_days'].mean():.2f}")
c2.metric("On-time vs type SLA", f"{tx['on_time'].mean() * 100:.1f}%")
c3.metric("Same-day share", f"{(tx['delivery_type'] == 'Same Day').mean() * 100:.1f}%")
st.plotly_chart(px.histogram(tx, x="delivery_days", color="delivery_type", barmode="overlay", title="Delivery days by type"), use_container_width=True)
geo = tx.groupby(["customer_state", "customer_tier"], as_index=False).agg(avg_days=("delivery_days", "mean"), on_time=("on_time", "mean"), orders=("transaction_id", "count"))
st.plotly_chart(px.bar(geo, x="customer_state", y="avg_days", color="customer_tier", barmode="group", title="Average delivery days by state and tier"), use_container_width=True)

st.header("Q22 · Payment analytics")
pay = tx.groupby(["order_year", "payment_method"], as_index=False).size()
st.plotly_chart(px.area(pay, x="order_year", y="size", color="payment_method", groupnorm="fraction", title="Payment mix over time"), use_container_width=True)
pay_kpi = tx.groupby("payment_method_group", as_index=False).agg(orders=("transaction_id", "count"), revenue=("final_amount_inr", "sum"), aov=("final_amount_inr", "mean"))
st.dataframe(pay_kpi.sort_values("revenue", ascending=False), use_container_width=True)
st.caption("No gateway success/failure flag exists. Mix, AOV and hierarchy are the available payment KPIs.")

st.header("Q23 · Returns & cancellations")
tx["is_return"] = tx["return_status"].eq("Returned")
tx["is_cancel"] = tx["return_status"].eq("Cancelled")
c1, c2, c3 = st.columns(3)
c1.metric("Return rate", f"{tx['is_return'].mean() * 100:.2f}%")
c2.metric("Cancel rate", f"{tx['is_cancel'].mean() * 100:.2f}%")
c3.metric("Returned GMV", inr(float(tx.loc[tx['is_return'], 'final_amount_inr'].sum())))
by_cat = (
    tx.groupby("subcategory")
    .agg(return_rate=("is_return", "mean"), cancel_rate=("is_cancel", "mean"))
    .reset_index()
)
returned_gmv = tx.loc[tx["is_return"]].groupby("subcategory")["final_amount_inr"].sum()
by_cat["returned_gmv"] = by_cat["subcategory"].map(returned_gmv).fillna(0.0)
st.plotly_chart(px.bar(by_cat, x="subcategory", y="return_rate", title="Return rate by subcategory", color_discrete_sequence=[AMAZON_ORANGE]), use_container_width=True)
st.dataframe(by_cat, use_container_width=True)

st.header("Q24 · Customer service")
st.caption("No complaint-category or resolution-time columns exist. CSAT is customer_rating; quality complaints are proxied by returns/cancellations.")
csat = tx.dropna(subset=["customer_rating"]).groupby("subcategory")["customer_rating"].mean().reset_index()
st.plotly_chart(px.bar(csat, x="subcategory", y="customer_rating", title="CSAT (mean customer rating)", range_y=[3, 5], color_discrete_sequence=[AMAZON_NAVY]), use_container_width=True)
tier_csat = tx.dropna(subset=["customer_rating"]).groupby("customer_tier")["customer_rating"].mean()
st.write(tier_csat.rename("mean_csat"))
c1, c2 = st.columns(2)
c1.metric("Overall CSAT (rated orders)", f"{tx['customer_rating'].mean():.2f} / 5")
c2.metric("Share of orders with a rating", f"{tx['customer_rating'].notna().mean() * 100:.1f}%")

st.header("Q25 · Supply chain")
st.caption("No supplier master is in the files. Brand is used as the fulfilment/vendor proxy; reliability is on-time delivery and return rate.")
vendor = (
    tx.assign(_on_time=tx["on_time"], _returned=tx["return_status"].eq("Returned"))
    .groupby("brand", as_index=False)
    .agg(
        orders=("transaction_id", "count"),
        on_time=("_on_time", "mean"),
        avg_days=("delivery_days", "mean"),
        return_rate=("_returned", "mean"),
        revenue=("final_amount_inr", "sum"),
    )
    .sort_values("revenue", ascending=False)
    .head(15)
)
st.plotly_chart(px.scatter(vendor, x="avg_days", y="return_rate", size="revenue", hover_name="brand", title="Vendor proxy: speed vs returns (size = revenue)"), use_container_width=True)
st.dataframe(vendor, use_container_width=True)
state_rel = tx.groupby("customer_state").agg(avg_days=("delivery_days", "mean"), on_time=("on_time", "mean"))
st.plotly_chart(px.bar(state_rel.reset_index(), x="customer_state", y="on_time", title="On-time rate by destination state"), use_container_width=True)
