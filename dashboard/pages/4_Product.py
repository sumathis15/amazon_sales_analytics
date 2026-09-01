"""Product & Inventory Analytics — Questions 16–20."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.utils import apply_filters, inr, load_products, load_transactions
from src.config import AMAZON_NAVY, AMAZON_ORANGE

st.set_page_config(page_title="Product Analytics", layout="wide")
st.title("Product & Inventory Analytics")
st.caption("Questions 16–20 · ranking, brands, demand, ratings, launches")

tx = apply_filters(load_transactions())
products = load_products()
if tx.empty:
    st.stop()

st.header("Q16 · Product performance")
prod = tx.groupby(["product_id", "product_name", "subcategory", "brand"], as_index=False).agg(
    revenue=("final_amount_inr", "sum"),
    units=("quantity", "sum"),
    rating=("product_rating", "mean"),
    customer_rating=("customer_rating", "mean"),
    return_rate=("return_status", lambda s: (s == "Returned").mean()),
)
metric = st.selectbox("Rank by", ["revenue", "units", "rating", "return_rate"])
asc = metric == "return_rate"
st.dataframe(prod.sort_values(metric, ascending=asc).head(25), use_container_width=True)
st.plotly_chart(px.bar(prod.nlargest(15, "revenue"), x="product_name", y="revenue", color="subcategory", title="Top 15 products by revenue"), use_container_width=True)

st.header("Q17 · Brand analytics")
brand_year = tx.groupby(["order_year", "brand"], as_index=False)["final_amount_inr"].sum()
top_brands = tx.groupby("brand")["final_amount_inr"].sum().nlargest(8).index
fig = px.line(brand_year[brand_year["brand"].isin(top_brands)], x="order_year", y="final_amount_inr", color="brand", markers=True, title="Top brand revenue over time")
st.plotly_chart(fig, use_container_width=True)
share = brand_year[brand_year["brand"].isin(top_brands)].copy()
share["share"] = share["final_amount_inr"] / share.groupby("order_year")["final_amount_inr"].transform("sum")
st.plotly_chart(px.area(share, x="order_year", y="share", color="brand", title="Brand share among top 8"), use_container_width=True)

st.header("Q18 · Inventory / demand")
demand = tx.assign(year_month=tx["order_date"].dt.to_period("M").astype(str))
monthly = demand.groupby(["year_month", "subcategory"], as_index=False).agg(units=("quantity", "sum"), revenue=("final_amount_inr", "sum"))
st.plotly_chart(px.line(monthly, x="year_month", y="units", color="subcategory", title="Monthly unit demand by subcategory"), use_container_width=True)
turnover = tx.groupby("product_id").agg(units=("quantity", "sum"), active_days=("order_date", lambda s: (s.max() - s.min()).days + 1))
turnover["units_per_day"] = turnover["units"] / turnover["active_days"].clip(lower=1)
st.caption(f"Median product velocity: {turnover['units_per_day'].median():.3f} units/day across SKUs sold in view.")
season = tx.groupby("order_month")["quantity"].sum().reset_index()
st.plotly_chart(px.bar(season, x="order_month", y="quantity", title="Seasonal unit demand (month of year)", color_discrete_sequence=[AMAZON_ORANGE]), use_container_width=True)

st.header("Q19 · Ratings & reviews")
st.plotly_chart(px.histogram(tx, x="product_rating", nbins=20, title="Product rating distribution", color_discrete_sequence=[AMAZON_NAVY]), use_container_width=True)
rated = prod.dropna(subset=["customer_rating"])
st.plotly_chart(px.scatter(rated, x="rating", y="revenue", color="subcategory", size="units", title="Catalog rating vs revenue", log_y=True), use_container_width=True)
st.caption("Review text is not in the files; rating columns are the available quality signal.")

st.header("Q20 · New product launches")
catalog = products[["product_id", "launch_year"]].drop_duplicates()
launched = tx.merge(catalog, on="product_id", how="left")
first_year = launched[launched["order_year"] == launched["launch_year"]]
launch_perf = first_year.groupby(["launch_year", "subcategory"], as_index=False).agg(first_year_revenue=("final_amount_inr", "sum"), units=("quantity", "sum"), skus=("product_id", "nunique"))
st.plotly_chart(px.bar(launch_perf, x="launch_year", y="first_year_revenue", color="subcategory", title="First-year revenue of newly launched SKUs"), use_container_width=True)
success = first_year.groupby("product_id").agg(revenue=("final_amount_inr", "sum"), units=("quantity", "sum"), rating=("product_rating", "mean"), name=("product_name", "first"))
st.subheader("Strongest launches in view (first-year revenue)")
st.dataframe(success.nlargest(15, "revenue"), use_container_width=True)
