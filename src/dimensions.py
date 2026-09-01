"""Customer, product, and time dimensions used by SQL, EDA, and Streamlit."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.config import CLEANED_DIR, REPORTS_DIR, RFM_SEGMENT_MAP


def assign_rfm_segment(r: int, f: int, m: int) -> str:
    if r >= 4 and f >= 4 and m >= 4:
        return "Champions"
    if r >= 4 and f >= 3 and m >= 3:
        return "Loyal Customers"
    if r >= 4 and f <= 2 and m >= 3:
        return "Potential Loyalists"
    if r >= 4 and f <= 2:
        return "New Customers" if f == 1 else "Promising"
    if r == 3 and f >= 3 and m >= 3:
        return "Loyal Customers"
    if r == 3 and f >= 3:
        return "Need Attention"
    if r == 3 and m >= 4:
        return "Need Attention"
    if r == 3:
        return "About to Sleep"
    if r <= 2 and f >= 4 and m >= 4:
        return "Cannot Lose Them"
    if r <= 2 and f >= 3:
        return "At Risk"
    if r <= 2 and m >= 4:
        return "At Risk"
    if r == 2:
        return "Hibernating"
    return "Lost"


def build_customers(tx: pd.DataFrame) -> pd.DataFrame:
    snapshot = tx["order_date"].max() + pd.Timedelta(days=1)
    work = tx.assign(
        _returned=tx["return_status"].eq("Returned").astype(float),
    )
    last_values = (
        work.sort_values("order_date")
        .groupby("customer_id")
        .agg(
            customer_city=("customer_city", "last"),
            customer_state=("customer_state", "last"),
            customer_tier=("customer_tier", "last"),
            customer_spending_tier=("customer_spending_tier", "last"),
            customer_age_group=("customer_age_group", "last"),
            is_prime_member=("is_prime_member", "max"),
        )
    )
    agg = work.groupby("customer_id").agg(
        first_order_date=("order_date", "min"),
        last_order_date=("order_date", "max"),
        frequency=("transaction_id", "nunique"),
        monetary=("final_amount_inr", "sum"),
        units=("quantity", "sum"),
        avg_order_value=("final_amount_inr", "mean"),
        avg_rating=("customer_rating", "mean"),
        return_rate=("_returned", "mean"),
    )
    customers = last_values.join(agg)
    customers["recency_days"] = (snapshot - customers["last_order_date"]).dt.days
    tenure_days = (customers["last_order_date"] - customers["first_order_date"]).dt.days.clip(lower=0)
    customers["tenure_days"] = tenure_days
    customers["acquisition_year"] = customers["first_order_date"].dt.year.astype(int)

    customers["r_score"] = pd.qcut(customers["recency_days"], 5, labels=[5, 4, 3, 2, 1]).astype(int)
    customers["f_score"] = _safe_qcut_score(customers["frequency"])
    customers["m_score"] = _safe_qcut_score(customers["monetary"])
    customers["rfm_segment"] = [
        assign_rfm_segment(r, f, m)
        for r, f, m in zip(customers["r_score"], customers["f_score"], customers["m_score"])
    ]
    customers["rfm_action"] = customers["rfm_segment"].map(RFM_SEGMENT_MAP)
    orders_per_year = customers["frequency"] / (tenure_days / 365.25).clip(lower=1 / 12)
    customers["clv"] = (customers["avg_order_value"] * orders_per_year * 3).clip(lower=customers["monetary"])
    customers = customers.reset_index()
    return customers


def _safe_qcut_score(series: pd.Series) -> pd.Series:
    """5 = highest frequency/monetary. Falls back when ties collapse bins."""
    try:
        return pd.qcut(series.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    except ValueError:
        return pd.cut(series.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)


def build_time_dimension(tx: pd.DataFrame) -> pd.DataFrame:
    dates = pd.date_range(tx["order_date"].min(), tx["order_date"].max(), freq="D")
    time_dim = pd.DataFrame({"date": dates})
    time_dim["year"] = time_dim["date"].dt.year
    time_dim["quarter"] = time_dim["date"].dt.quarter
    time_dim["month"] = time_dim["date"].dt.month
    time_dim["month_name"] = time_dim["date"].dt.strftime("%b")
    time_dim["week"] = time_dim["date"].dt.isocalendar().week.astype(int)
    time_dim["day"] = time_dim["date"].dt.day
    time_dim["day_of_week"] = time_dim["date"].dt.dayofweek
    time_dim["day_name"] = time_dim["date"].dt.strftime("%A")
    time_dim["is_weekend"] = time_dim["day_of_week"].isin([5, 6])
    time_dim["year_month"] = time_dim["date"].dt.strftime("%Y-%m")
    time_dim["year_quarter"] = (
        time_dim["year"].astype(str) + "-Q" + time_dim["quarter"].astype(str)
    )
    festival_dates = (
        tx.loc[tx["is_festival_sale"], ["order_date", "festival_name"]]
        .dropna()
        .drop_duplicates(subset=["order_date"])
    )
    time_dim = time_dim.merge(
        festival_dates.rename(columns={"order_date": "date"}),
        on="date",
        how="left",
    )
    time_dim["is_festival"] = time_dim["festival_name"].notna()
    return time_dim


def build_product_metrics(tx: pd.DataFrame, catalog: pd.DataFrame) -> pd.DataFrame:
    work = tx.assign(_returned=tx["return_status"].eq("Returned").astype(float))
    metrics = work.groupby("product_id").agg(
        units_sold=("quantity", "sum"),
        orders=("transaction_id", "nunique"),
        revenue=("final_amount_inr", "sum"),
        avg_discount=("discount_percent", "mean"),
        avg_customer_rating=("customer_rating", "mean"),
        return_rate=("_returned", "mean"),
        first_sold=("order_date", "min"),
        last_sold=("order_date", "max"),
    )
    products = catalog.merge(metrics, on="product_id", how="left")
    products["units_sold"] = products["units_sold"].fillna(0).astype(int)
    products["orders"] = products["orders"].fillna(0).astype(int)
    products["revenue"] = products["revenue"].fillna(0.0)
    return products


def run_dimensions(tx: pd.DataFrame | None = None, catalog: pd.DataFrame | None = None) -> dict:
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    if tx is None:
        tx = pd.read_parquet(CLEANED_DIR / "transactions_cleaned.parquet")
    if catalog is None:
        catalog = pd.read_parquet(CLEANED_DIR / "products_catalog_cleaned.parquet")

    print("Building customer RFM dimension...")
    customers = build_customers(tx)
    print("Building time dimension...")
    time_dim = build_time_dimension(tx)
    print("Building product metrics...")
    products = build_product_metrics(tx, catalog)

    customers.to_parquet(CLEANED_DIR / "customers.parquet", index=False)
    time_dim.to_parquet(CLEANED_DIR / "time_dimension.parquet", index=False)
    products.to_parquet(CLEANED_DIR / "products.parquet", index=False)
    customers.to_csv(CLEANED_DIR / "customers.csv", index=False)
    products.to_csv(CLEANED_DIR / "products.csv", index=False)

    summary = {
        "customers": int(len(customers)),
        "rfm_segments": {str(k): int(v) for k, v in customers["rfm_segment"].value_counts().items()},
        "time_rows": int(len(time_dim)),
        "products": int(len(products)),
        "snapshot_date": str((tx["order_date"].max() + pd.Timedelta(days=1)).date()),
    }
    (REPORTS_DIR / "dimension_metrics.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(f"Customers {len(customers):,} | products {len(products):,} | dates {len(time_dim):,}")
    return {"customers": customers, "time_dim": time_dim, "products": products, "summary": summary}


if __name__ == "__main__":
    run_dimensions()
