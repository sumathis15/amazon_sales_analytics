"""Shared Streamlit helpers: cached loaders, filters, KPI cards."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import CITY_COORDS, CLEANED_DIR, DB_PATH, PALETTE

LINKEDIN_URL = "https://www.linkedin.com/in/sumathisaravanan/"
DEVELOPER_NAME = "Sumathi S"


def render_developer_credit() -> None:
    """Pinned 'Developed by' block at the bottom of the sidebar."""
    st.markdown(
        """
<style>
section[data-testid="stSidebar"] {
    position: relative;
}
.developer-credit {
    position: sticky;
    bottom: 0;
    margin-top: 1.75rem;
    background: #15202b;
    border-radius: 12px;
    padding: 14px 16px 12px 16px;
    box-shadow: 0 0 0 1px rgba(255,255,255,0.06);
}
.developer-credit .credit-label {
    font-size: 11px;
    letter-spacing: 0.14em;
    color: #9bb0c9;
    font-weight: 650;
    margin-bottom: 10px;
}
.developer-credit a {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #ffffff !important;
    text-decoration: none !important;
    font-weight: 600;
    font-size: 0.98rem;
}
.developer-credit a:hover { opacity: 0.88; }
.developer-credit .li-badge {
    width: 22px;
    height: 22px;
    border-radius: 4px;
    background: #0A66C2;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: -0.04em;
    color: #fff;
}
</style>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        f"""
<div class="developer-credit">
  <div class="credit-label">DEVELOPED BY</div>
  <a href="{LINKEDIN_URL}" target="_blank" rel="noopener noreferrer">
    <span class="li-badge">in</span>
    <span>{DEVELOPER_NAME}</span>
  </a>
</div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner="Loading cleaned transactions...")
def load_transactions() -> pd.DataFrame:
    path = CLEANED_DIR / "transactions_cleaned.parquet"
    df = pd.read_parquet(path)
    df["order_date"] = pd.to_datetime(df["order_date"])
    return df


@st.cache_data(show_spinner="Loading customer dimension...")
def load_customers() -> pd.DataFrame:
    return pd.read_parquet(CLEANED_DIR / "customers.parquet")


@st.cache_data(show_spinner="Loading product dimension...")
def load_products() -> pd.DataFrame:
    return pd.read_parquet(CLEANED_DIR / "products.parquet")


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    years = sorted(df["order_year"].unique())
    subcats = sorted(df["subcategory"].unique())
    states = sorted(df["customer_state"].unique())
    st.sidebar.header("Filters")
    year_from, year_to = st.sidebar.select_slider(
        "Year range",
        options=years,
        value=(min(years), max(years)),
    )
    chosen_sub = st.sidebar.multiselect("Subcategory", subcats, default=subcats)
    chosen_state = st.sidebar.multiselect("State", states, default=states)
    prime = st.sidebar.selectbox("Prime membership", ["All", "Prime", "Non-Prime"])
    festival = st.sidebar.selectbox("Festival sales", ["All", "Festival only", "Non-festival"])
    out = df[(df["order_year"] >= year_from) & (df["order_year"] <= year_to)]
    if chosen_sub:
        out = out[out["subcategory"].isin(chosen_sub)]
    if chosen_state:
        out = out[out["customer_state"].isin(chosen_state)]
    if prime == "Prime":
        out = out[out["is_prime_member"]]
    elif prime == "Non-Prime":
        out = out[~out["is_prime_member"]]
    if festival == "Festival only":
        out = out[out["is_festival_sale"]]
    elif festival == "Non-festival":
        out = out[~out["is_festival_sale"]]
    st.sidebar.caption(f"{len(out):,} of {len(df):,} orders in view")
    render_developer_credit()
    return out


def kpi_row(items: list[tuple[str, str, str | None]]) -> None:
    cols = st.columns(len(items))
    for col, (label, value, delta) in zip(cols, items):
        col.metric(label, value, delta=delta)


def inr(value: float, digits: int = 1) -> str:
    if abs(value) >= 1e7:
        return f"₹{value / 1e7:,.{digits}f} Cr"
    if abs(value) >= 1e5:
        return f"₹{value / 1e5:,.{digits}f} L"
    return f"₹{value:,.0f}"


def yoy_delta(current: float, previous: float) -> str | None:
    if previous == 0 or pd.isna(previous) or pd.isna(current):
        return None
    return f"{(current / previous - 1) * 100:+.1f}%"
