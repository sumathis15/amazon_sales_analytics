"""Shared Streamlit helpers: cached loaders, filters, KPI cards."""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import pandas as pd
import streamlit as st

warnings.filterwarnings("ignore", message=".*keyword arguments have been deprecated.*")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import CLEANED_DIR

LINKEDIN_URL = "https://www.linkedin.com/in/sumathisaravanan/"
DEVELOPER_NAME = "Sumathi S"

def inject_theme() -> None:
    """Apply chrome immediately so the Streamlit header cannot cover titles."""
    st.markdown(
        """
<style>
/* Amazon analytics workspace — navy / orange / warm parchment */
.stApp {
    background:
        radial-gradient(1200px 420px at 12% -8%, rgba(255, 153, 0, 0.22), transparent 55%),
        radial-gradient(900px 380px at 100% 0%, rgba(20, 110, 180, 0.12), transparent 50%),
        linear-gradient(180deg, #FFF6E7 0%, #F6F1E8 42%, #EEF2F6 100%);
    font-family: "Amazon Ember", "Helvetica Neue", Arial, sans-serif;
}
[data-testid="stHeader"],
header[data-testid="stHeader"],
div[data-testid="stDecoration"] {
    display: none !important;
    height: 0 !important;
}
#MainMenu, footer { visibility: hidden; }
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #131A22 0%, #232F3E 55%, #1B2430 100%) !important;
    border-right: 3px solid #FF9900;
}
[data-testid="stSidebarNavSeparator"] { display: none; }
[data-testid="stSidebarNav"] { padding-bottom: 0.15rem !important; }
[data-testid="stSidebarNav"] a span { color: #EAEDED !important; }
[data-testid="stSidebarNav"] a:hover { background: rgba(255, 153, 0, 0.16); }
[data-testid="stSidebarNav"] a[aria-current="page"] {
    background: rgba(255, 153, 0, 0.22);
    border-left: 3px solid #FF9900;
}
[data-testid="stSidebarNav"] a[href]:not([href=""]):has(span) {
    border-radius: 8px;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
[data-testid="stSidebar"] label {
    color: #FEBD69 !important;
}
.developer-credit {
    margin: 0;
    padding: 0.15rem 0 0.7rem 0;
    border-bottom: 1px solid rgba(254, 189, 105, 0.28);
    background: transparent;
}
.developer-credit .credit-label {
    font-size: 10px;
    letter-spacing: 0.12em;
    color: #FEBD69;
    font-weight: 650;
    margin-bottom: 6px;
}
.developer-credit a {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #FFFFFF !important;
    text-decoration: none !important;
    font-weight: 600;
    font-size: 0.92rem;
}
.developer-credit a:hover { color: #FEBD69 !important; }
.developer-credit .li-badge {
    width: 18px;
    height: 18px;
    border-radius: 3px;
    background: #0A66C2;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    font-size: 9px;
    font-weight: 800;
    color: #fff;
}
div[data-testid="stSidebarContent"] div[data-testid="stMarkdownContainer"]:has(.developer-credit) {
    padding-top: 0 !important;
    margin-bottom: 0.2rem !important;
}
.block-container { padding-top: 1.1rem !important; }
h1 {
    color: #232F3E !important;
    letter-spacing: -0.02em;
}
h1::after {
    content: "";
    display: block;
    width: 5.5rem;
    height: 4px;
    margin-top: 0.45rem;
    background: linear-gradient(90deg, #FF9900, #FEBD69);
    border-radius: 4px;
}
h2, h3 { color: #232F3E !important; }
[data-testid="stCaptionContainer"] p { color: #5A6570 !important; }
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid rgba(35, 47, 62, 0.08);
    border-left: 4px solid #FF9900;
    border-radius: 12px;
    padding: 0.55rem 0.75rem 0.45rem 0.8rem;
    box-shadow: 0 6px 18px rgba(35, 47, 62, 0.06);
}
[data-testid="stMetricLabel"] { color: #5A6570 !important; }
[data-testid="stMetricValue"] { color: #232F3E !important; }
[data-testid="stPlotlyChart"] {
    background: rgba(255, 255, 255, 0.78);
    border: 1px solid rgba(35, 47, 62, 0.07);
    border-radius: 14px;
    padding: 0.2rem 0.2rem 0;
}
[data-testid="stImage"] img {
    max-height: 420px !important;
    width: auto !important;
    max-width: 100% !important;
    height: auto !important;
    object-fit: contain !important;
}
[data-testid="stAlert"] {
    border-left: 4px solid #FF9900;
    background: rgba(255, 255, 255, 0.88);
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_developer_credit() -> None:
    """Theme + compact credit line in the sidebar, under the page list and above filters."""
    inject_theme()
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


_CATEGORY_COLS = (
    "category",
    "subcategory",
    "brand",
    "customer_city",
    "customer_state",
    "customer_tier",
    "customer_spending_tier",
    "customer_age_group",
    "payment_method",
    "payment_method_group",
    "delivery_type",
    "return_status",
    "festival_name",
    "product_name",
)


def _optimise_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Shrink dtypes so the warehouse fits Streamlit Cloud RAM."""
    if "order_date" in df.columns:
        df["order_date"] = pd.to_datetime(df["order_date"])
    for col in _CATEGORY_COLS:
        if col in df.columns:
            df[col] = df[col].astype("category")
    for col in df.select_dtypes(include=["float64"]).columns:
        df[col] = pd.to_numeric(df[col], downcast="float")
    for col in df.select_dtypes(include=["int64"]).columns:
        df[col] = pd.to_numeric(df[col], downcast="integer")
    return df


@st.cache_resource(show_spinner="Loading cleaned transactions...")
def load_transactions() -> pd.DataFrame:
    path = CLEANED_DIR / "transactions_cleaned.parquet"
    if not path.exists():
        st.error(
            "Cleaned warehouse is missing (`data/cleaned/transactions_cleaned.parquet`). "
            "On Streamlit Cloud this file must be in the GitHub repo."
        )
        st.stop()
    return _optimise_frame(pd.read_parquet(path))


@st.cache_resource(show_spinner="Loading customer dimension...")
def load_customers() -> pd.DataFrame:
    return _optimise_frame(pd.read_parquet(CLEANED_DIR / "customers.parquet"))


@st.cache_resource(show_spinner="Loading product dimension...")
def load_products() -> pd.DataFrame:
    return _optimise_frame(pd.read_parquet(CLEANED_DIR / "products.parquet"))


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    render_developer_credit()
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
    return out.copy()


def kpi_row(items: list[tuple[str, str, str | None]]) -> None:
    cols = st.columns(len(items))
    for col, (label, value, delta) in zip(cols, items):
        col.metric(label, value, delta=delta)


def show_chart(fig, height: int = 400) -> None:
    """Plotly charts at one dashboard height so none blow up the page."""
    if hasattr(fig, "update_layout"):
        fig.update_layout(height=height, autosize=True)
    st.plotly_chart(fig, width="stretch")


def show_figure(path: Path | str) -> None:
    """EDA PNGs share the same width stretch; CSS caps height to 420px."""
    st.image(str(path), width="stretch")


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
