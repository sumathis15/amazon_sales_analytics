"""Post-cleaning verification: every claim is computed from the cleaned files."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from src.config import CLEANED_DIR, REPORTS_DIR


def main() -> None:
    df = pd.read_parquet(CLEANED_DIR / "transactions_cleaned.parquet")
    metrics = json.loads((REPORTS_DIR / "cleaning_metrics.json").read_text(encoding="utf-8"))
    print("rows", len(df), "expected", metrics["rows_after"])
    print("cols", list(df.columns))
    print("date range", df["order_date"].min(), df["order_date"].max())
    print("nulls:\n", df.isna().sum()[df.isna().sum() > 0].to_string())

    print("\nQ1 dates dtype", df["order_date"].dtype, "nat", int(df["order_date"].isna().sum()))
    print("year vs dt.year mismatch", int((df["order_year"] != df["order_date"].dt.year).sum()))
    print("month mismatch", int((df["order_month"] != df["order_date"].dt.month).sum()))

    print("\nQ2 original_price dtype", df["original_price_inr"].dtype)
    print(df["original_price_inr"].describe().to_string())
    print("neg prices", int((df["original_price_inr"] < 0).sum()), "null", int(df["original_price_inr"].isna().sum()))
    expected = df["discounted_price_inr"] / (1 - df["discount_percent"] / 100)
    rel = (df["original_price_inr"] - expected).abs() / expected
    print("price vs discount identity rel>0.01", int((rel > 0.01).sum()), "max", float(rel.max()))

    print("\nQ3 ratings unique", sorted(df["customer_rating"].dropna().unique().tolist()))
    print("rating min/max", df["customer_rating"].min(), df["customer_rating"].max())
    print("rating nulls", int(df["customer_rating"].isna().sum()), f"{df['customer_rating'].isna().mean():.2%}")

    print("\nQ4 cities", df["customer_city"].nunique())
    print(df["customer_city"].value_counts().to_string())

    print("\nQ5 booleans")
    for c in ["is_prime_member", "is_prime_eligible", "is_festival_sale"]:
        print(c, df[c].dtype, df[c].value_counts().to_dict())

    print("\nQ6 category", df["category"].unique().tolist())
    print("subcategory", df["subcategory"].unique().tolist())

    print("\nQ7 delivery", df["delivery_days"].min(), df["delivery_days"].max(), df["delivery_days"].unique().tolist())
    print(pd.crosstab(df["delivery_days"], df["delivery_type"]).to_string())

    print("\nQ8 txn unique", df["transaction_id"].nunique(), "dups", int(df["transaction_id"].duplicated().sum()))
    print("_DUP remaining", int(df["transaction_id"].str.endswith("_DUP").sum()))
    key = ["customer_id", "product_id", "order_date", "final_amount_inr"]
    print("key dups", int(df.duplicated(key).sum()))

    print("\nQ9 orig max", float(df["original_price_inr"].max()), "p99", float(df["original_price_inr"].quantile(0.99)))

    print("\nQ10 payment")
    print(df["payment_method"].value_counts().to_string())
    print(df["payment_method_group"].value_counts().to_string())

    print("\nage")
    print(df["customer_age_group"].value_counts().to_string())
    print("\nrevenue", float(df["final_amount_inr"].sum()))
    print("customers", df["customer_id"].nunique(), "products", df["product_id"].nunique())


if __name__ == "__main__":
    main()
