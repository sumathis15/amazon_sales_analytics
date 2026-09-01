"""Data Cleaning Practice Questions 1–10."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import REPORTS_DIR
from dashboard.utils import render_developer_credit

st.set_page_config(page_title="Data Cleaning", layout="wide")
render_developer_credit()
st.title("Data Cleaning Practice Questions")
st.caption("10 challenges from the brief · answers verified on the raw CSVs and the cleaned parquet")

report = REPORTS_DIR / "data_cleaning_report.md"
if not report.exists():
    st.error("Run `python -m src.cleaning` then `python scripts/run_pipeline.py` to generate the cleaning report.")
    st.stop()

text = report.read_text(encoding="utf-8")
chunks = text.split("## Question ")
st.markdown(chunks[0])

prompts = {
    "1": "Clean and standardise all dates to YYYY-MM-DD, handling invalid dates.",
    "2": "Clean original_price_inr to numeric INR (₹, commas, Price on Request).",
    "3": "Standardise customer ratings to 1.0–5.0; handle missing values strategically.",
    "4": "Standardise city names (Bangalore/Bengaluru, Mumbai/Bombay, Delhi/New Delhi, typos).",
    "5": "Convert boolean columns to True/False (Yes/No, 1/0, Y/N).",
    "6": "Standardise product category names.",
    "7": "Clean delivery_days to valid numeric days (negatives, 'Same Day', 50-day outliers).",
    "8": "Distinguish genuine bulk orders from duplicate data errors.",
    "9": "Correct 100x price outliers from decimal-point errors.",
    "10": "Standardise payment methods and create a categorical hierarchy.",
}

for chunk in chunks[1:]:
    num, body = chunk.split("\n", 1)
    qnum = num.strip().split("—")[0].strip().split()[0]
    title = num.strip()
    with st.expander(f"Question {title}", expanded=True):
        if qnum in prompts:
            st.info(prompts[qnum])
        st.markdown(body)

st.caption("Code: `src/cleaning.py` · metrics: `reports/cleaning_metrics.json` · cleaned tables: `data/cleaned/`")
