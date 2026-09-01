"""Deeper inspection for cleaning-rule design: dates, prices, cities, dups, outliers."""

from __future__ import annotations

import glob
import os
import re
from collections import Counter

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(__file__))


def load() -> pd.DataFrame:
    frames = [pd.read_csv(p, dtype=str, keep_default_na=False) for p in sorted(glob.glob(os.path.join(ROOT, "amazon_india_20*.csv")))]
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    df = load()

    print("=== ALL CITY VALUES ===")
    for v, c in df["customer_city"].value_counts().items():
        print(f"{c:>8,}  {repr(v)}")

    print("\n=== DATE: non-ISO unique count and invalid parse attempts ===")
    dates = df["order_date"].astype(str)
    iso = dates.str.fullmatch(r"\d{4}-\d{2}-\d{2}")
    slash = dates.str.fullmatch(r"\d{2}/\d{2}/\d{4}")
    dash4 = dates.str.fullmatch(r"\d{2}-\d{2}-\d{4}")
    dash2 = dates.str.fullmatch(r"\d{2}-\d{2}-\d{2}")
    print("iso", int(iso.sum()), "slash", int(slash.sum()), "dash4", int(dash4.sum()), "dash2", int(dash2.sum()), "other", int((~iso & ~slash & ~dash4 & ~dash2).sum()))

    # Check day>12 vs month>12 to infer DD/MM vs MM/DD
    slash_vals = dates[slash]
    d1 = slash_vals.str.split("/").str[0].astype(int)
    d2 = slash_vals.str.split("/").str[1].astype(int)
    print("slash first>12:", int((d1 > 12).sum()), "second>12:", int((d2 > 12).sum()), "both<=12:", int(((d1 <= 12) & (d2 <= 12)).sum()))
    print("slash first>31:", int((d1 > 31).sum()), "second>31:", int((d2 > 31).sum()))
    print("slash month-like invalid 13-99 in first:", int(((d1 >= 13) & (d1 <= 99) & (d1 > 31)).sum()))

    dash_vals = dates[dash4]
    a1 = dash_vals.str.split("-").str[0].astype(int)
    a2 = dash_vals.str.split("-").str[1].astype(int)
    print("dash4 first>12:", int((a1 > 12).sum()), "second>12:", int((a2 > 12).sum()), "both<=12:", int(((a1 <= 12) & (a2 <= 12)).sum()))

    # Cross-check with order_year / order_month
    sample = df.loc[slash, ["order_date", "order_month", "order_year", "order_quarter"]].head(20)
    print("\nslash vs month/year:\n", sample.to_string(index=False))
    sample2 = df.loc[dash4, ["order_date", "order_month", "order_year"]].head(15)
    print("\ndash4 vs month/year:\n", sample2.to_string(index=False))

    # Invalid calendar dates
    def try_parse(s, fmt):
        return pd.to_datetime(s, format=fmt, errors="coerce")

    parsed_slash_dmy = try_parse(slash_vals, "%d/%m/%Y")
    parsed_slash_mdy = try_parse(slash_vals, "%m/%d/%Y")
    print("slash parse DMY fail", int(parsed_slash_dmy.isna().sum()), "MDY fail", int(parsed_slash_mdy.isna().sum()))
    if parsed_slash_dmy.isna().any():
        print("DMY fail examples", slash_vals[parsed_slash_dmy.isna()].value_counts().head(20).to_string())
    parsed_dash = try_parse(dash_vals, "%d-%m-%Y")
    print("dash4 DMY fail", int(parsed_dash.isna().sum()))
    if parsed_dash.isna().any():
        print(dash_vals[parsed_dash.isna()].value_counts().head(20).to_string())

    # Compare parsed month to order_month
    tmp = df.loc[slash, ["order_date", "order_month", "order_year"]].copy()
    tmp["dmy"] = try_parse(tmp["order_date"], "%d/%m/%Y")
    tmp["mdy"] = try_parse(tmp["order_date"], "%m/%d/%Y")
    tmp["om"] = pd.to_numeric(tmp["order_month"], errors="coerce")
    tmp["oy"] = pd.to_numeric(tmp["order_year"], errors="coerce")
    print("slash DMY month match order_month", int((tmp["dmy"].dt.month == tmp["om"]).sum()), "/", len(tmp))
    print("slash MDY month match order_month", int((tmp["mdy"].dt.month == tmp["om"]).sum()), "/", len(tmp))
    print("slash DMY year match order_year", int((tmp["dmy"].dt.year == tmp["oy"]).sum()), "/", len(tmp))

    tmp2 = df.loc[dash4, ["order_date", "order_month", "order_year"]].copy()
    tmp2["dmy"] = try_parse(tmp2["order_date"], "%d-%m-%Y")
    tmp2["om"] = pd.to_numeric(tmp2["order_month"], errors="coerce")
    tmp2["oy"] = pd.to_numeric(tmp2["order_year"], errors="coerce")
    print("dash4 DMY month match", int((tmp2["dmy"].dt.month == tmp2["om"]).sum()), "/", len(tmp2))
    print("dash4 DMY year match", int((tmp2["dmy"].dt.year == tmp2["oy"]).sum()), "/", len(tmp2))

    print("\n=== PRICE TEXT VALUES (non-numeric after rupee/comma strip) ===")
    raw = df["original_price_inr"].astype(str)
    cleaned = raw.str.replace("₹", "", regex=False).str.replace(",", "", regex=False).str.replace("Rs.", "", regex=False).str.replace("Rs", "", regex=False).str.replace("INR", "", case=False, regex=False).str.strip()
    num = pd.to_numeric(cleaned, errors="coerce")
    bad = raw[num.isna() & raw.str.strip().ne("")]
    print(bad.value_counts().head(40).to_string())
    print("bad count", len(bad))

    print("\n=== NEGATIVE original_price ===")
    num2 = pd.to_numeric(cleaned, errors="coerce")
    print("neg count", int((num2 < 0).sum()), "zero", int((num2 == 0).sum()))
    print(df.loc[num2 < 0, ["product_id", "product_name", "original_price_inr", "discounted_price_inr", "final_amount_inr", "quantity"]].head(10).to_string())

    print("\n=== PRICE OUTLIERS vs discounted ===")
    df["_orig"] = num2
    df["_disc"] = pd.to_numeric(df["discounted_price_inr"], errors="coerce")
    df["_final"] = pd.to_numeric(df["final_amount_inr"], errors="coerce")
    df["_qty"] = pd.to_numeric(df["quantity"], errors="coerce")
    ratio = df["_orig"] / df["_disc"]
    print("orig/disc describe:\n", ratio.replace([pd.NA], pd.NA).describe(percentiles=[0.01, 0.05, 0.5, 0.95, 0.99, 0.999]).to_string())
    print("ratio > 50", int((ratio > 50).sum()), ">90", int((ratio > 90).sum()), ">100", int((ratio > 100).sum()))
    print("ratio < 0.01", int((ratio < 0.01).sum()), "<0.02", int((ratio < 0.02).sum()))
    print("high ratio examples:")
    hi = df.loc[ratio > 50, ["product_id", "original_price_inr", "_orig", "_disc", "_final", "discount_percent"]].head(15)
    print(hi.to_string())

    print("\norig vs catalog base_price")
    cat = pd.read_csv(os.path.join(ROOT, "amazon_india_products_catalog.csv"))
    print(cat["category"].value_counts().to_string())
    print("catalog unique cats", cat["category"].unique().tolist())
    print("catalog subcats", cat["subcategory"].unique().tolist())
    print("base_price describe", cat["base_price_2015"].describe().to_string())

    print("\n=== DUPLICATE KEY EXAMPLES ===")
    key = ["customer_id", "product_id", "order_date", "final_amount_inr"]
    dups = df[df.duplicated(key, keep=False)].sort_values(key + ["transaction_id"])
    print("dup rows", len(dups), "dup groups", dups.groupby(key).ngroups)
    # compare other columns within groups
    print(dups.head(12)[["transaction_id"] + key + ["quantity", "order_month", "payment_method", "customer_city"]].to_string())
    # how many groups have different quantity / txn
    g = dups.groupby(key)
    print("groups with >1 unique txn", int((g["transaction_id"].nunique() > 1).sum()))
    print("groups with same qty", int((g["quantity"].nunique() == 1).sum()))
    print("groups size value counts:\n", g.size().value_counts().to_string())
    # check if other fields differ
    vary_cols = []
    for col in df.columns:
        if col in key:
            continue
        if (g[col].nunique() > 1).any():
            vary_cols.append((col, int((g[col].nunique() > 1).sum())))
    print("cols that vary within dup groups:", vary_cols[:30])

    print("\n=== DELIVERY_DAYS vs delivery_type ===")
    print(pd.crosstab(df["delivery_days"], df["delivery_type"]).to_string())

    print("\n=== PAYMENT all unique repr ===")
    print(df["payment_method"].value_counts().to_string())

    print("\n=== AGE GROUP vs other ===")
    print(df["customer_age_group"].value_counts(dropna=False).to_string())

    print("\n=== DELIVERY CHARGES ===")
    dc = pd.to_numeric(df["delivery_charges"], errors="coerce")
    print(dc.describe().to_string())
    print("null", int(dc.isna().sum()), "zero", int((dc == 0).sum()), "neg", int((dc < 0).sum()))
    print("by prime:\n", df.assign(dc=dc).groupby("is_prime_member")["dc"].agg(["mean", "median", lambda s: s.isna().mean()]).head(10).to_string())

    print("\n=== RETURN STATUS ===")
    print(df["return_status"].value_counts().to_string())

    print("\n=== DISCOUNT vs prices consistency sample ===")
    # discounted should be orig * (1-disc/100)
    ok = num2.notna() & df["_disc"].notna()
    expected = df.loc[ok, "_orig"] * (1 - pd.to_numeric(df.loc[ok, "discount_percent"], errors="coerce") / 100)
    rel = (expected - df.loc[ok, "_disc"]).abs() / df.loc[ok, "_disc"].replace(0, pd.NA)
    print("rel err describe", rel.describe(percentiles=[0.5, 0.9, 0.99]).to_string())
    print("rel err > 0.05", int((rel > 0.05).sum()), ">0.5", int((rel > 0.5).sum()))


if __name__ == "__main__":
    main()
