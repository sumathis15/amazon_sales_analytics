"""EDA Questions 1–20 with verified charts and write-ups."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import FIGURES_DIR, REPORTS_DIR
from dashboard.utils import render_developer_credit, show_figure

st.set_page_config(page_title="EDA", layout="wide")
render_developer_credit()
st.title("Exploratory Data Analysis Questions")
st.caption("20 visualisation challenges from the brief · figures and numbers computed from the cleaned warehouse")

report = REPORTS_DIR / "eda_insights.md"
if not report.exists() or not FIGURES_DIR.exists():
    st.error("Run `python scripts/run_pipeline.py` to generate EDA figures and insights.")
    st.stop()

FIGURES = {
    1: ["01_revenue_trend.png"],
    2: ["02_seasonality.png", "02b_seasonality_category.png"],
    3: ["03_rfm_segmentation.png"],
    4: ["04_payment_evolution.png"],
    5: ["05_category_performance.png", "05b_category_treemap.png"],
    6: ["06_prime_impact.png"],
    7: ["07_geography.png"],
    8: ["08_festival_impact.png"],
    9: ["09_age_demographics.png"],
    10: ["10_price_demand.png"],
    11: ["11_delivery_performance.png"],
    12: ["12_returns.png"],
    13: ["13_brand_performance.png"],
    14: ["14_clv_cohort.png"],
    15: ["15_discount_effectiveness.png"],
    16: ["16_ratings_sales.png"],
    17: ["17_customer_journey.png"],
    18: ["18_product_lifecycle.png"],
    19: ["19_competitive_pricing.png"],
    20: ["20_business_health.png"],
}

PROMPTS = {
    1: "Yearly revenue growth 2015–2025 with % growth, trend line, and annotated growth periods.",
    2: "Seasonal patterns: monthly heatmaps, peak months, year and category comparison.",
    3: "RFM segmentation with scatter plots and actionable groups.",
    4: "Payment-method evolution: rise of UPI, decline of COD, stacked shares.",
    5: "Category performance: treemap, bars, pies for contribution, growth, share.",
    6: "Prime vs non-Prime: AOV, frequency, category mix.",
    7: "Geographic performance by city, state, and tier (Metro/Tier1/Tier2/Rural).",
    8: "Festival impact: before/during/after, Diwali, Prime Day, time series.",
    9: "Age-group behaviour: category mix, spend, frequency.",
    10: "Price vs demand: scatter and correlation across categories.",
    11: "Delivery days, on-time performance, rating vs speed.",
    12: "Return patterns vs ratings, prices, and categories.",
    13: "Brand performance and market-share evolution.",
    14: "CLV, cohort retention curves, distribution by segment and acquisition year.",
    15: "Discount effectiveness vs volume and revenue.",
    16: "Product ratings vs sales across categories and price bands.",
    17: "Customer journey: frequency, category transitions, first purchase to loyal.",
    18: "Product lifecycle and category mix over the decade.",
    19: "Competitive pricing: brand positioning, ranges, penetration.",
    20: "Business-health multi-panel: growth, acquisition, retention, operations.",
}

text = report.read_text(encoding="utf-8")
parts = re.split(r"\n## Question ", text)
st.markdown(parts[0])

for part in parts[1:]:
    header, body = part.split("\n", 1)
    match = re.match(r"(\d+)", header)
    if not match:
        continue
    qn = int(match.group(1))
    st.header(f"Question {header}")
    st.info(PROMPTS.get(qn, ""))
    files = FIGURES.get(qn, [])
    if len(files) == 1:
        path = FIGURES_DIR / files[0]
        if path.exists():
            show_figure(path)
    elif files:
        cols = st.columns(len(files))
        for col, name in zip(cols, files):
            path = FIGURES_DIR / name
            if path.exists():
                with col:
                    show_figure(path)
    st.markdown(body)
    st.divider()

st.caption("Code: `src/eda.py` · write-up: `reports/eda_insights.md` · PNGs: `reports/eda_figures/`")
