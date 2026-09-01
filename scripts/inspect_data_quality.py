"""Inspect raw Amazon India transaction files for data-quality issues.

This script is diagnostic only: it reports what is actually in the data
so cleaning rules can be designed from evidence, not assumptions.
"""

from __future__ import annotations

import glob
import os
import re
from collections import Counter

import pandas as pd

RAW_GLOB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "amazon_india_20*.csv")
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")


def load_all_as_str() -> pd.DataFrame:
    frames = []
    for path in sorted(glob.glob(RAW_GLOB)):
        frames.append(pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[]))
        print(f"loaded {os.path.basename(path)}: {len(frames[-1]):,} rows")
    return pd.concat(frames, ignore_index=True)


def value_profile(series: pd.Series, n: int = 40) -> None:
    vc = series.value_counts(dropna=False)
    print(f"  unique={series.nunique(dropna=False):,}  null-like={((series=='') | series.isna()).sum():,}")
    print("  top values:")
    for val, cnt in vc.head(n).items():
        print(f"    {cnt:>8,}  |  {repr(val)[:120]}")


def date_format_profile(series: pd.Series) -> None:
    samples = series.fillna("").astype(str)
    patterns = Counter()
    invalid_examples = []
    for v in samples.sample(min(len(samples), 200000), random_state=42):
        if v in ("", "nan", "None", "NULL", "NaT"):
            patterns["EMPTY/NULL"] += 1
        elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            patterns["YYYY-MM-DD"] += 1
        elif re.fullmatch(r"\d{2}/\d{2}/\d{4}", v):
            patterns["DD/MM/YYYY or MM/DD/YYYY"] += 1
        elif re.fullmatch(r"\d{2}-\d{2}-\d{2}", v):
            patterns["DD-MM-YY"] += 1
        elif re.fullmatch(r"\d{2}-\d{2}-\d{4}", v):
            patterns["DD-MM-YYYY"] += 1
        elif re.fullmatch(r"\d{4}/\d{2}/\d{2}", v):
            patterns["YYYY/MM/DD"] += 1
        else:
            patterns[f"OTHER:{v[:40]}"] += 1
            if len(invalid_examples) < 20:
                invalid_examples.append(v)
    print("  date format sample (200k rows):")
    for k, c in patterns.most_common(30):
        print(f"    {c:>8,}  {k}")
    if invalid_examples:
        print("  other examples:", invalid_examples[:15])


def price_profile(series: pd.Series) -> None:
    samples = series.fillna("").astype(str)
    patterns = Counter()
    other = []
    for v in samples:
        if v in ("", "nan", "None", "NULL"):
            patterns["EMPTY/NULL"] += 1
        elif re.fullmatch(r"-?\d+(\.\d+)?", v):
            patterns["PLAIN_NUMERIC"] += 1
        elif "₹" in v or "Rs" in v or "INR" in v.upper():
            patterns["CURRENCY_SYMBOL"] += 1
        elif "," in v:
            patterns["COMMA_SEPARATOR"] += 1
        elif re.search(r"[A-Za-z]", v):
            patterns[f"TEXT:{v[:40]}"] += 1
            if len(other) < 25:
                other.append(v)
        else:
            patterns[f"OTHER:{v[:40]}"] += 1
            if len(other) < 25:
                other.append(v)
    print("  price format counts (full column):")
    for k, c in patterns.most_common(40):
        print(f"    {c:>8,}  {k}")
    if other:
        print("  text/other examples:", other[:20])


def rating_profile(series: pd.Series) -> None:
    vc = series.fillna("<<NA>>").astype(str).value_counts()
    print(f"  unique rating strings={len(vc)}")
    for val, cnt in vc.head(50).items():
        print(f"    {cnt:>8,}  |  {repr(val)}")


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    df = load_all_as_str()
    print(f"\nTOTAL ROWS: {len(df):,}  COLS: {len(df.columns)}")
    print("COLUMNS:", list(df.columns))

    empty_like = ["", "nan", "NaN", "None", "NULL", "null", "NA", "n/a", "N/A"]
    print("\n=== NULL / EMPTY PROFILE (string-aware) ===")
    for col in df.columns:
        s = df[col].astype(str).str.strip()
        n = s.isin(empty_like).sum()
        if n:
            print(f"  {col:28s}  {n:>10,}  ({100*n/len(df):5.2f}%)")

    print("\n=== Q1 ORDER_DATE FORMATS ===")
    date_format_profile(df["order_date"])
    print("  unique sample of non YYYY-MM-DD:")
    mask = ~df["order_date"].astype(str).str.fullmatch(r"\d{4}-\d{2}-\d{2}", na=False)
    print("  non-iso count:", int(mask.sum()))
    print(df.loc[mask, "order_date"].value_counts().head(30).to_string())

    print("\n=== Q2 ORIGINAL_PRICE FORMATS ===")
    price_profile(df["original_price_inr"])
    print("  discounted_price_inr:")
    price_profile(df["discounted_price_inr"])
    print("  final_amount_inr:")
    price_profile(df["final_amount_inr"])
    print("  delivery_charges:")
    price_profile(df["delivery_charges"])
    print("  subtotal_inr:")
    price_profile(df["subtotal_inr"])

    print("\n=== Q3 CUSTOMER_RATING ===")
    rating_profile(df["customer_rating"])
    print("  product_rating:")
    rating_profile(df["product_rating"])

    print("\n=== Q4 CUSTOMER_CITY ===")
    value_profile(df["customer_city"], 80)
    print("\n=== CUSTOMER_STATE ===")
    value_profile(df["customer_state"], 50)
    print("\n=== CUSTOMER_TIER ===")
    value_profile(df["customer_tier"], 30)

    print("\n=== Q5 BOOLEANS ===")
    for col in ["is_prime_member", "is_prime_eligible", "is_festival_sale"]:
        print(f"\n  -- {col} --")
        value_profile(df[col], 30)

    print("\n=== Q6 CATEGORY / SUBCATEGORY / BRAND ===")
    value_profile(df["category"], 40)
    print("\n  subcategory:")
    value_profile(df["subcategory"], 40)
    print("\n  brand unique:", df["brand"].nunique())
    print(df["brand"].value_counts().head(20).to_string())

    print("\n=== Q7 DELIVERY_DAYS ===")
    value_profile(df["delivery_days"], 50)
    print("\n  delivery_type:")
    value_profile(df["delivery_type"], 20)

    print("\n=== Q8 DUPLICATES ===")
    print("  exact row dups:", int(df.duplicated().sum()))
    print("  txn_id dups:", int(df["transaction_id"].duplicated().sum()))
    key = ["customer_id", "product_id", "order_date", "final_amount_inr"]
    print("  key dups (cust,prod,date,amount):", int(df.duplicated(key).sum()))
    print("  txn_id unique:", df["transaction_id"].nunique())

    print("\n=== Q10 PAYMENT_METHOD ===")
    value_profile(df["payment_method"], 50)

    print("\n=== OTHER CATEGORICALS ===")
    for col in [
        "customer_spending_tier",
        "customer_age_group",
        "return_status",
        "festival_name",
        "quantity",
    ]:
        print(f"\n  -- {col} --")
        value_profile(df[col], 25)

    print("\n=== NUMERIC-LOOKING COLUMNS (raw string min/max after coerce) ===")
    for col in [
        "original_price_inr",
        "discounted_price_inr",
        "final_amount_inr",
        "discount_percent",
        "quantity",
        "delivery_days",
        "product_weight_kg",
        "product_rating",
        "customer_rating",
    ]:
        raw = df[col].astype(str).str.replace(",", "", regex=False).str.replace("₹", "", regex=False)
        num = pd.to_numeric(raw, errors="coerce")
        print(
            f"  {col:24s} numeric={num.notna().sum():,}  "
            f"non-numeric={(num.isna() & df[col].astype(str).str.strip().ne('')).sum():,}  "
            f"min={num.min()} max={num.max()} median={num.median()}"
        )


if __name__ == "__main__":
    main()
