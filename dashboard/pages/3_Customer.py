"""Customer Analytics — Questions 11–15."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.utils import apply_filters, inr, load_customers, load_transactions
from src.config import AMAZON_NAVY, AMAZON_ORANGE

st.set_page_config(page_title="Customer Analytics", layout="wide")
st.title("Customer Analytics")
st.caption("Questions 11–15 · RFM, journey, Prime, retention, demographics")

tx = apply_filters(load_transactions())
customers = load_customers()
if tx.empty:
    st.stop()

active_ids = tx["customer_id"].unique()
cust = customers[customers["customer_id"].isin(active_ids)]

st.header("Q11 · Customer segmentation (RFM)")
seg = cust.groupby("rfm_segment", as_index=False).agg(customers=("customer_id", "count"), revenue=("monetary", "sum"), avg_clv=("clv", "mean"), recency=("recency_days", "mean"))
c1, c2 = st.columns(2)
with c1:
    fig = px.bar(seg.sort_values("revenue", ascending=False), x="rfm_segment", y="revenue", title="Revenue by RFM segment", color_discrete_sequence=[AMAZON_ORANGE])
    st.plotly_chart(fig, use_container_width=True)
with c2:
    sample = cust.sample(min(8000, len(cust)), random_state=1)
    fig = px.scatter(sample, x="recency_days", y="frequency", color="rfm_segment", size="monetary", size_max=18, title="RFM scatter")
    st.plotly_chart(fig, use_container_width=True)
st.dataframe(seg.sort_values("revenue", ascending=False), use_container_width=True)
pick = st.selectbox("Inspect segment playbook", sorted(cust["rfm_segment"].unique()))
st.info(cust.loc[cust["rfm_segment"] == pick, "rfm_action"].iloc[0])
profile = cust[cust["rfm_segment"] == pick][["customer_id", "customer_city", "customer_tier", "monetary", "frequency", "recency_days", "clv"]].nlargest(15, "monetary")
st.dataframe(profile, use_container_width=True)

st.header("Q12 · Customer journey")
freq = tx.groupby("customer_id").size()
freq_band = pd.cut(freq, bins=[0, 1, 2, 4, 8, 10_000], labels=["1 order", "2", "3-4", "5-8", "9+"]).value_counts().rename_axis("band").reset_index(name="customers")
st.plotly_chart(px.bar(freq_band, x="band", y="customers", title="Purchase frequency bands", color_discrete_sequence=[AMAZON_NAVY]), use_container_width=True)
seq = tx.sort_values("order_date").groupby("customer_id")["subcategory"].agg(["first", "last"])
seq = seq[seq["first"] != seq["last"]].value_counts().reset_index(name="customers")
seq.columns = ["first_category", "latest_category", "customers"]
st.plotly_chart(px.sunburst(seq.head(40), path=["first_category", "latest_category"], values="customers", title="First → latest subcategory (switchers)"), use_container_width=True)

st.header("Q13 · Prime membership")
prime_tx = tx.groupby("is_prime_member").agg(orders=("transaction_id", "count"), revenue=("final_amount_inr", "sum"), aov=("final_amount_inr", "mean"), delivery=("delivery_days", "mean"), rating=("customer_rating", "mean"))
prime_tx.index = prime_tx.index.map({True: "Prime", False: "Non-Prime"})
st.dataframe(prime_tx, use_container_width=True)
yearly = tx.groupby(["order_year", "is_prime_member"], as_index=False).agg(aov=("final_amount_inr", "mean"), share=("transaction_id", "count"))
yearly["is_prime_member"] = yearly["is_prime_member"].map({True: "Prime", False: "Non-Prime"})
st.plotly_chart(px.line(yearly, x="order_year", y="aov", color="is_prime_member", markers=True, title="AOV Prime vs non-Prime"), use_container_width=True)
retain = cust.groupby("is_prime_member")["frequency"].mean()
st.caption(f"Mean orders per customer — Prime {retain.get(True, float('nan')):.2f} vs non-Prime {retain.get(False, float('nan')):.2f}.")

st.header("Q14 · Retention & cohorts")
first = tx.groupby("customer_id")["order_date"].min().dt.year.rename("acq_year")
merged = tx[["customer_id", "order_year"]].merge(first, on="customer_id")
merged["period"] = merged["order_year"] - merged["acq_year"]
cohort = merged.groupby(["acq_year", "period"])["customer_id"].nunique().unstack(fill_value=0)
retention = cohort.div(cohort[0].replace(0, pd.NA), axis=0)
st.plotly_chart(px.imshow(retention, aspect="auto", color_continuous_scale="YlOrBr", title="Annual cohort retention"), use_container_width=True)
st.caption("Churn proxy: customers whose last order is older than 365 days from the data snapshot.")
snapshot = tx["order_date"].max()
churned = (cust["last_order_date"] < snapshot - pd.Timedelta(days=365)).mean()
st.metric("Inactive 365+ days (in-view customers)", f"{churned * 100:.1f}%")

st.header("Q15 · Demographics & behaviour")
age = tx.groupby(["customer_age_group", "subcategory"], as_index=False)["final_amount_inr"].sum()
st.plotly_chart(px.bar(age, x="customer_age_group", y="final_amount_inr", color="subcategory", title="Spending by age × subcategory"), use_container_width=True)
geo_age = tx.groupby(["customer_tier", "customer_age_group"], as_index=False)["final_amount_inr"].mean()
st.plotly_chart(px.density_heatmap(geo_age, x="customer_age_group", y="customer_tier", z="final_amount_inr", title="AOV heatmap: tier × age"), use_container_width=True)
