"""
Data cleaning pipeline for Amazon India transactions.

Every rule below is based on values actually observed in the raw CSVs
(see scripts/inspect_data_quality.py). The ten practice questions map
1:1 onto the functions in this module.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.config import (
    CATEGORY_ALIASES,
    CATALOG_FILE,
    CITY_ALIASES,
    CLEANED_DIR,
    DELIVERY_TYPE_DAYS,
    FALSE_VALUES,
    PAYMENT_ALIASES,
    PAYMENT_HIERARCHY,
    RAW_DIR,
    REPORTS_DIR,
    TRANSACTION_GLOB,
    TRUE_VALUES,
)

NULL_TOKENS = {"", "nan", "none", "null", "na", "n/a", "nat"}
PRICE_TEXT_TOKENS = {"price on request", "por", "tbd", "na", "n/a"}


def _is_null_token(value: Any) -> bool:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return True
    return str(value).strip().lower() in NULL_TOKENS


# ---------------------------------------------------------------------------
# Question 1 — order_date formats
# ---------------------------------------------------------------------------
def parse_order_date(value: Any, order_month: Any = None, order_year: Any = None) -> pd.Timestamp:
    """Standardise a date string to a Timestamp (UTC-naive calendar date).

    Observed formats in the files:
    - YYYY-MM-DD (majority, always consistent with order_month/order_year)
    - DD-MM-YYYY (always day-month-year; 100% match to order_month)
    - DD/MM/YYYY mixed with MM/DD/YYYY (slash dates are ambiguous)

    Slash dates are disambiguated with order_month, which matched one of
    the two numeric parts on every inspected row. Invalid calendar dates
    (e.g. 32/13/2020) return NaT.
    """
    if _is_null_token(value):
        return pd.NaT
    text = str(value).strip()

    iso = pd.to_datetime(text, format="%Y-%m-%d", errors="coerce")
    if pd.notna(iso):
        return iso.normalize()

    dash = pd.to_datetime(text, format="%d-%m-%Y", errors="coerce")
    if pd.notna(dash):
        return dash.normalize()

    dash_yy = pd.to_datetime(text, format="%d-%m-%y", errors="coerce")
    if pd.notna(dash_yy):
        return dash_yy.normalize()

    slash = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if slash:
        a, b, y = int(slash.group(1)), int(slash.group(2)), int(slash.group(3))
        month_hint = pd.to_numeric(pd.Series([order_month]), errors="coerce").iloc[0]
        year_hint = pd.to_numeric(pd.Series([order_year]), errors="coerce").iloc[0]
        if pd.notna(year_hint) and int(year_hint) != y:
            y = int(year_hint)

        def _valid(day: int, month: int, year: int) -> pd.Timestamp:
            try:
                return pd.Timestamp(year=year, month=month, day=day)
            except (ValueError, TypeError):
                return pd.NaT

        if a > 12 and b <= 12:
            return _valid(a, b, y)
        if b > 12 and a <= 12:
            return _valid(b, a, y)
        if pd.notna(month_hint):
            mh = int(month_hint)
            if mh == b:
                return _valid(a, b, y)
            if mh == a:
                return _valid(b, a, y)
        # Last resort: Indian default DD/MM/YYYY
        parsed = _valid(a, b, y)
        if pd.notna(parsed):
            return parsed
        return _valid(b, a, y)

    return pd.to_datetime(text, errors="coerce", dayfirst=True)


def _parse_slash_dates(raw: pd.Series, months: pd.Series, years: pd.Series) -> pd.Series:
    """Vectorised DMY/MDY disambiguation for slash-separated dates."""
    parts = raw.str.split("/", expand=True)
    first = pd.to_numeric(parts[0], errors="coerce")
    second = pd.to_numeric(parts[1], errors="coerce")
    year = pd.to_numeric(parts[2], errors="coerce")
    month_hint = pd.to_numeric(months, errors="coerce")
    year_hint = pd.to_numeric(years, errors="coerce")
    year = year_hint.where(year_hint.notna(), year)

    use_dmy = (first > 12) & (second <= 12)
    use_mdy = (second > 12) & (first <= 12)
    both_ok = (first <= 12) & (second <= 12)
    use_dmy = use_dmy | (both_ok & (month_hint == second))
    use_mdy = use_mdy | (both_ok & (month_hint == first) & (month_hint != second))

    day = np.where(use_dmy, first, np.where(use_mdy, second, first))
    month = np.where(use_dmy, second, np.where(use_mdy, first, second))
    assembled = (
        year.astype("Int64").astype(str)
        + "-"
        + pd.Series(month, index=raw.index).astype("Int64").astype(str).str.zfill(2)
        + "-"
        + pd.Series(day, index=raw.index).astype("Int64").astype(str).str.zfill(2)
    )
    return pd.to_datetime(assembled, format="%Y-%m-%d", errors="coerce")


def clean_order_dates(df: pd.DataFrame, metrics: dict) -> pd.DataFrame:
    raw = df["order_date"].astype(str).str.strip()
    iso_mask = raw.str.fullmatch(r"\d{4}-\d{2}-\d{2}")
    slash_mask = raw.str.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}")
    dash_mask = raw.str.fullmatch(r"\d{1,2}-\d{1,2}-\d{4}")
    dash_yy_mask = raw.str.fullmatch(r"\d{1,2}-\d{1,2}-\d{2}")

    parsed = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    parsed.loc[iso_mask] = pd.to_datetime(raw[iso_mask], format="%Y-%m-%d", errors="coerce")
    parsed.loc[dash_mask] = pd.to_datetime(raw[dash_mask], format="%d-%m-%Y", errors="coerce")
    parsed.loc[dash_yy_mask] = pd.to_datetime(raw[dash_yy_mask], format="%d-%m-%y", errors="coerce")
    if slash_mask.any():
        parsed.loc[slash_mask] = _parse_slash_dates(
            raw[slash_mask],
            df.loc[slash_mask, "order_month"],
            df.loc[slash_mask, "order_year"],
        )
    leftover = parsed.isna() & ~raw.map(_is_null_token)
    if leftover.any():
        parsed.loc[leftover] = pd.to_datetime(raw[leftover], errors="coerce", dayfirst=True)

    df["order_date"] = parsed
    invalid = int(df["order_date"].isna().sum())
    metrics["q1_date"] = {
        "iso_yyyy_mm_dd": int(iso_mask.sum()),
        "slash_mixed": int(slash_mask.sum()),
        "dash_dd_mm_yyyy": int(dash_mask.sum()),
        "dash_dd_mm_yy": int(dash_yy_mask.sum()),
        "invalid_or_unparseable": invalid,
        "standardized_valid": int(df["order_date"].notna().sum()),
        "rule": (
            "ISO dates kept as-is. Dash dates parsed as DD-MM-YYYY. "
            "Slash dates disambiguated using order_month (DMY vs MDY mix). "
            "Unparseable/invalid calendar dates set to NaT and later dropped."
        ),
    }
    if invalid:
        df = df.dropna(subset=["order_date"]).copy()
    df["order_year"] = df["order_date"].dt.year.astype(int)
    df["order_month"] = df["order_date"].dt.month.astype(int)
    df["order_quarter"] = df["order_date"].dt.quarter.astype(int)
    df["order_day"] = df["order_date"].dt.day.astype(int)
    return df


# ---------------------------------------------------------------------------
# Question 2 — original_price_inr mixed types
# ---------------------------------------------------------------------------
def parse_price(value: Any) -> float:
    """Convert messy price text to a float INR amount, else NaN.

    Observed: plain numbers, comma grouping (21,947.26), rupee prefix (₹32,095.73),
    Rs prefix (Rs 49,035). 'Price on Request' is handled but was not present.
    """
    if _is_null_token(value):
        return np.nan
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = str(value).strip()
    if text.lower() in PRICE_TEXT_TOKENS:
        return np.nan
    text = text.replace("₹", "").replace("\u20b9", "")
    text = re.sub(r"(?i)\bINR\b", "", text)
    text = re.sub(r"(?i)\bRs\.?\b", "", text)
    text = text.replace(",", "").strip()
    try:
        return float(text)
    except ValueError:
        return np.nan


def clean_original_price(df: pd.DataFrame, metrics: dict) -> pd.DataFrame:
    raw = df["original_price_inr"].astype(str)
    parsed = raw.map(parse_price)
    currency_count = int(raw.str.contains(r"₹|Rs|INR", case=False, regex=True).sum())
    comma_count = int(raw.str.contains(",").sum())
    negative_count = int((parsed < 0).sum())
    unparsed = int(parsed.isna().sum())

    discounted = pd.to_numeric(df["discounted_price_inr"].map(parse_price), errors="coerce")
    pct = pd.to_numeric(df["discount_percent"], errors="coerce").clip(lower=0, upper=99.99)
    expected = discounted / (1.0 - pct / 100.0)
    expected = expected.where(pct < 100, discounted)

    working = parsed.abs()
    ratio = working / expected.replace(0, np.nan)
    fix_100x = ratio.between(50, 500)
    fix_10x = ratio.between(5, 20)
    working = working.mask(fix_100x, working / 100.0)
    working = working.mask(fix_10x, working / 10.0)

    still_bad = working.isna() | ((working - expected).abs() / expected.replace(0, np.nan) > 0.5)
    recovered_from_expected = int(still_bad.sum())
    working = working.mask(still_bad, expected)

    df["original_price_inr"] = working.round(2)
    metrics["q2_price"] = {
        "currency_symbol_rows": currency_count,
        "comma_separator_rows": comma_count,
        "unparsed_including_price_on_request": unparsed,
        "negative_sign_errors": negative_count,
        "rule": (
            "Stripped ₹ / Rs / INR and thousands separators; abs() for sign errors; "
            "non-numeric/Price on Request imputed from discounted_price / (1 - discount%)."
        ),
    }
    metrics["q9_outliers"] = {
        "corrected_100x_decimal_shift": int(fix_100x.sum()),
        "corrected_10x_decimal_shift": int(fix_10x.sum()),
        "rebuilt_from_discount_identity": recovered_from_expected,
        "rule": (
            "Compared parsed original_price to expected = discounted_price / (1 - discount%). "
            "Ratios ~100 were decimal-point (paise) errors and divided by 100; "
            "ratios ~10 divided by 10. Remaining mismatches used the discount identity."
        ),
    }
    return df


# ---------------------------------------------------------------------------
# Question 3 — customer ratings
# ---------------------------------------------------------------------------
def parse_rating(value: Any) -> float:
    """Normalise rating strings onto a 1.0–5.0 scale."""
    if _is_null_token(value):
        return np.nan
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        return number if 1.0 <= number <= 5.0 else np.nan
    text = str(value).strip().lower()
    text = text.replace("stars", "").replace("star", "").strip()
    if "/" in text:
        left, right = text.split("/", 1)
        try:
            numerator = float(left.strip())
            denominator = float(right.strip())
        except ValueError:
            return np.nan
        if denominator == 0:
            return np.nan
        number = numerator if abs(denominator - 5) < 1e-6 else (numerator / denominator) * 5.0
    else:
        try:
            number = float(text)
        except ValueError:
            return np.nan
    if number < 1.0 or number > 5.0:
        return np.nan
    return round(float(number), 1)


def clean_ratings(df: pd.DataFrame, metrics: dict) -> pd.DataFrame:
    raw = df["customer_rating"]
    parsed = raw.map(parse_rating)
    missing_before = int(raw.map(_is_null_token).sum())
    format_rows = int((~raw.map(_is_null_token) & parsed.notna() & ~pd.to_numeric(raw, errors="coerce").notna()).sum())

    df["product_rating"] = pd.to_numeric(df["product_rating"].map(parse_rating), errors="coerce")
    product_median = parsed.groupby(df["product_id"]).transform("median")
    imputed = parsed.fillna(product_median).fillna(df["product_rating"])
    imputed = imputed.clip(1.0, 5.0).round(1)

    # Strategic choice: keep the parsed rating with NaN for genuine non-response
    # so satisfaction analyses are not diluted. Provide an imputed companion
    # only for completeness checks; downstream KPIs use customer_rating (nullable).
    df["customer_rating"] = parsed
    df["customer_rating_imputed"] = imputed
    metrics["q3_rating"] = {
        "missing_before": missing_before,
        "missing_after_parse": int(parsed.isna().sum()),
        "non_plain_numeric_formats": format_rows,
        "imputed_companion_filled": int(parsed.isna().sum()),
        "rule": (
            "Parsed '4.5', '4 stars', '3/5', '2.5/5.0' onto 1–5. "
            "Missing ratings left as NaN for analysis (30%+ are true non-response). "
            "customer_rating_imputed uses product-level median, then product_rating."
        ),
    }
    return df


# ---------------------------------------------------------------------------
# Question 4 — customer_city
# ---------------------------------------------------------------------------
def standardise_city(value: Any) -> str | float:
    if _is_null_token(value):
        return np.nan
    key = re.sub(r"\s+", " ", str(value).strip()).casefold()
    if key in CITY_ALIASES:
        return CITY_ALIASES[key]
    return str(value).strip().title()


def clean_cities(df: pd.DataFrame, metrics: dict) -> pd.DataFrame:
    before_unique = int(df["customer_city"].nunique())
    normalised = df["customer_city"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    mapped = normalised.str.casefold().map(CITY_ALIASES)
    df["customer_city"] = mapped.fillna(normalised.str.title())
    mapped_rows = int((normalised != df["customer_city"]).sum())
    df["customer_state"] = df["customer_state"].astype(str).str.strip()
    df["customer_tier"] = df["customer_tier"].astype(str).str.strip()
    metrics["q4_city"] = {
        "unique_before": before_unique,
        "unique_after": int(df["customer_city"].nunique()),
        "rows_standardised": mapped_rows,
        "rule": (
            "Trimmed whitespace, folded case, mapped Bombay→Mumbai, "
            "New Delhi/Delhi NCR→Delhi, Bengaluru/Banglore/Bengalore→Bangalore, "
            "Calcutta→Kolkata, Madras/chenai→Chennai, plus typo 'mumba'."
        ),
    }
    return df


# ---------------------------------------------------------------------------
# Question 5 — boolean columns
# ---------------------------------------------------------------------------
def parse_bool(value: Any) -> bool | float:
    if _is_null_token(value):
        return np.nan
    if isinstance(value, bool):
        return value
    key = str(value).strip().lower()
    if key in TRUE_VALUES:
        return True
    if key in FALSE_VALUES:
        return False
    return np.nan


def clean_booleans(df: pd.DataFrame, metrics: dict) -> pd.DataFrame:
    summary = {}
    for col in ["is_prime_member", "is_prime_eligible", "is_festival_sale"]:
        before = df[col].astype(str).value_counts(dropna=False).to_dict()
        parsed = df[col].map(parse_bool)
        missing = int(parsed.isna().sum())
        if missing:
            # Festival flag: empty means not a festival sale. Prime flags: False.
            parsed = parsed.fillna(False)
        df[col] = parsed.astype(bool)
        summary[col] = {
            "raw_value_counts": {str(k): int(v) for k, v in before.items()},
            "true_after": int(df[col].sum()),
            "false_after": int((~df[col]).sum()),
        }
    metrics["q5_booleans"] = {
        "columns": summary,
        "rule": "Mapped True/TRUE/Yes/1/Y and False/FALSE/No/0/N onto boolean. Residual missing → False.",
    }
    df["festival_name"] = df["festival_name"].where(
        ~df["festival_name"].map(_is_null_token),
        np.nan,
    )
    df.loc[~df["is_festival_sale"], "festival_name"] = np.nan
    return df


# ---------------------------------------------------------------------------
# Question 6 — product categories
# ---------------------------------------------------------------------------
def standardise_category(value: Any) -> str | float:
    if _is_null_token(value):
        return np.nan
    key = re.sub(r"\s+", " ", str(value).strip()).casefold()
    return CATEGORY_ALIASES.get(key, str(value).strip().title())


def clean_categories(df: pd.DataFrame, metrics: dict) -> pd.DataFrame:
    before = df["category"].value_counts().to_dict()
    df["category"] = df["category"].map(standardise_category)
    df["subcategory"] = df["subcategory"].astype(str).str.strip()
    df["brand"] = df["brand"].astype(str).str.strip()
    metrics["q6_category"] = {
        "raw_value_counts": {str(k): int(v) for k, v in before.items()},
        "unique_after": int(df["category"].nunique()),
        "after_value_counts": {str(k): int(v) for k, v in df["category"].value_counts().items()},
        "rule": (
            "Mapped Electronic / ELECTRONICS / Electronics & Accessories / "
            "Electronicss → Electronics."
        ),
    }
    return df


# ---------------------------------------------------------------------------
# Question 7 — delivery_days
# ---------------------------------------------------------------------------
def parse_delivery_days(value: Any, delivery_type: Any) -> float:
    default = DELIVERY_TYPE_DAYS.get(str(delivery_type).strip(), 3)
    if _is_null_token(value):
        return float(default)
    text = str(value).strip().lower()
    if text in {"same day", "sameday"}:
        return 1.0
    if text in {"express"}:
        return 2.0
    range_match = re.fullmatch(r"(\d+)\s*-\s*(\d+)\s*days?", text)
    if range_match:
        low, high = int(range_match.group(1)), int(range_match.group(2))
        if str(delivery_type).strip() == "Same Day":
            return float(low)
        if str(delivery_type).strip() == "Express":
            return float(min(high, 2))
        return float(high)
    try:
        number = float(text)
    except ValueError:
        return float(default)
    if number < 0 or number > 10:
        return float(default)
    if number == 0:
        return 1.0 if str(delivery_type).strip() == "Same Day" else float(default)
    return float(int(number))


def clean_delivery_days(df: pd.DataFrame, metrics: dict) -> pd.DataFrame:
    raw = df["delivery_days"].astype(str)
    counts = raw.value_counts().to_dict()
    dtype = df["delivery_type"].astype(str).str.strip()
    default = dtype.map(DELIVERY_TYPE_DAYS).fillna(3).astype(float)
    text = raw.str.strip().str.lower()
    numeric = pd.to_numeric(raw, errors="coerce")

    result = default.copy()
    result = result.mask(text.isin({"same day", "sameday"}), 1.0)
    result = result.mask(text.eq("express"), 2.0)
    result = result.mask(text.eq("1-2 days") & dtype.eq("Same Day"), 1.0)
    result = result.mask(text.eq("1-2 days") & dtype.eq("Express"), 2.0)
    result = result.mask(text.eq("1-2 days") & ~dtype.isin(["Same Day", "Express"]), 2.0)
    valid_numeric = numeric.notna() & (numeric >= 1) & (numeric <= 10)
    result = result.mask(valid_numeric, numeric)
    result = result.mask((numeric == 0) & dtype.eq("Same Day"), 1.0)
    df["delivery_days"] = result.round(0).astype(int)
    df["delivery_type"] = dtype
    metrics["q7_delivery"] = {
        "raw_value_counts": {str(k): int(v) for k, v in counts.items()},
        "after_min": int(df["delivery_days"].min()),
        "after_max": int(df["delivery_days"].max()),
        "rule": (
            "Same Day text → 1; Express text → 2; '1-2 days' → 1/2 by delivery_type; "
            "negative and 15-day outliers imputed from delivery_type "
            "(Same Day=1, Express=2, Standard=3). Zero mapped to 1 for Same Day else type default."
        ),
    }
    return df


# ---------------------------------------------------------------------------
# Question 8 — duplicates
# ---------------------------------------------------------------------------
def handle_duplicates(df: pd.DataFrame, metrics: dict) -> pd.DataFrame:
    key = ["customer_id", "product_id", "order_date", "final_amount_inr"]
    key_dup_rows = int(df.duplicated(key).sum())
    dup_suffix = df["transaction_id"].astype(str).str.endswith("_DUP")
    dup_suffix_count = int(dup_suffix.sum())

    # Observed pattern: every key-duplicate pair is (TXN_id, TXN_id_DUP) with
    # identical quantity and payload — these are data errors, not bulk orders.
    # Genuine multi-unit purchases already appear as quantity 2 or 3 on a
    # single transaction_id.
    cleaned = df.loc[~dup_suffix].copy()
    remaining_key_dups = int(cleaned.duplicated(key).sum())
    exact_dups = int(cleaned.duplicated().sum())
    if remaining_key_dups:
        cleaned = cleaned.drop_duplicates(key, keep="first")
    if exact_dups:
        cleaned = cleaned.drop_duplicates(keep="first")

    metrics["q8_duplicates"] = {
        "exact_row_duplicates_before": int(df.duplicated().sum()),
        "transaction_id_duplicates_before": int(df["transaction_id"].duplicated().sum()),
        "key_duplicate_rows_before": key_dup_rows,
        "txn_id_dup_suffix_removed": dup_suffix_count,
        "key_duplicates_remaining_after_suffix_drop": remaining_key_dups,
        "rows_after": int(len(cleaned)),
        "rule": (
            "Pairs sharing customer, product, date and amount always included a "
            "transaction_id ending in _DUP. Those 5,610 rows are error clones "
            "(same quantity, not bulk orders) and were dropped. Unique _DUP-free "
            "transaction_ids were kept."
        ),
    }
    return cleaned


# ---------------------------------------------------------------------------
# Question 10 — payment methods
# ---------------------------------------------------------------------------
def standardise_payment(value: Any) -> str | float:
    if _is_null_token(value):
        return np.nan
    key = re.sub(r"\s+", " ", str(value).strip()).casefold()
    key = key.replace("_", " ")
    return PAYMENT_ALIASES.get(key, str(value).strip().title())


def clean_payments(df: pd.DataFrame, metrics: dict) -> pd.DataFrame:
    before = df["payment_method"].value_counts().to_dict()
    df["payment_method"] = df["payment_method"].map(standardise_payment)
    df["payment_method_group"] = df["payment_method"].map(PAYMENT_HIERARCHY).fillna("Other")
    metrics["q10_payment"] = {
        "raw_value_counts": {str(k): int(v) for k, v in before.items()},
        "after_value_counts": {str(k): int(v) for k, v in df["payment_method"].value_counts().items()},
        "hierarchy_counts": {str(k): int(v) for k, v in df["payment_method_group"].value_counts().items()},
        "rule": (
            "Canonical names: UPI, Credit Card, Debit Card, COD, Net Banking, Wallet, BNPL. "
            "Aliases PhonePe/GooglePay→UPI, CREDIT_CARD/CC→Credit Card, C.O.D→COD. "
            "Hierarchy groups: Digital Payments, Card Payments, Bank Transfer, "
            "Buy Now Pay Later, Cash on Delivery."
        ),
    }
    return df


# ---------------------------------------------------------------------------
# Additional missing-value handling (approach section, not a numbered Q)
# ---------------------------------------------------------------------------
def clean_remaining_fields(df: pd.DataFrame, metrics: dict) -> pd.DataFrame:
    df["delivery_charges"] = df["delivery_charges"].map(parse_price)
    dc_missing = int(df["delivery_charges"].isna().sum())
    df["delivery_charges"] = df["delivery_charges"].fillna(0.0)

    df["discount_percent"] = pd.to_numeric(df["discount_percent"], errors="coerce").clip(0, 100)
    df["discounted_price_inr"] = df["discounted_price_inr"].map(parse_price)
    df["subtotal_inr"] = df["subtotal_inr"].map(parse_price)
    df["final_amount_inr"] = df["final_amount_inr"].map(parse_price)
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(1).astype(int)
    df["product_weight_kg"] = pd.to_numeric(df["product_weight_kg"], errors="coerce")

    age_raw = df["customer_age_group"].where(~df["customer_age_group"].map(_is_null_token), np.nan)
    missing_age = int(age_raw.isna().sum())
    age_lookup = (
        pd.DataFrame({"customer_id": df["customer_id"], "age": age_raw})
        .dropna(subset=["age"])
        .groupby("customer_id")["age"]
        .first()
    )
    filled = age_raw.fillna(df["customer_id"].map(age_lookup))
    recovered = int(missing_age - filled.isna().sum())
    df["customer_age_group"] = filled.fillna("Unknown")

    df["customer_spending_tier"] = df["customer_spending_tier"].astype(str).str.strip()
    df["return_status"] = df["return_status"].astype(str).str.strip()
    df["product_name"] = df["product_name"].astype(str).str.strip()

    metrics["other_missing"] = {
        "delivery_charges_missing_filled_with_zero": dc_missing,
        "age_missing_before": missing_age,
        "age_recovered_from_same_customer": recovered,
        "age_left_as_unknown": int((df["customer_age_group"] == "Unknown").sum()),
        "rule": (
            "delivery_charges is 0 on ~all non-null rows (only 8 rows = 40 INR), so missing → 0. "
            "Age is constant per customer_id; missing ages were back-filled from the same "
            "customer's other orders. Remaining customers with no age anywhere → 'Unknown' "
            "(spending-tier age mix is uniform, so imputing 26-35 would only add bias)."
        ),
    }
    return df


def load_raw_transactions() -> pd.DataFrame:
    files = sorted(RAW_DIR.glob(TRANSACTION_GLOB))
    if not files:
        raise FileNotFoundError(f"No transaction CSVs matching {TRANSACTION_GLOB} in {RAW_DIR}")
    frames = []
    for path in files:
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        frame["source_file"] = path.name
        frames.append(frame)
        print(f"  loaded {path.name}: {len(frame):,} rows")
    return pd.concat(frames, ignore_index=True)


def load_catalog() -> pd.DataFrame:
    path = RAW_DIR / CATALOG_FILE
    catalog = pd.read_csv(path)
    catalog["category"] = catalog["category"].map(standardise_category)
    catalog["is_prime_eligible"] = catalog["is_prime_eligible"].map(parse_bool).astype(bool)
    catalog["product_name"] = catalog["product_name"].astype(str).str.strip()
    catalog["brand"] = catalog["brand"].astype(str).str.strip()
    catalog["subcategory"] = catalog["subcategory"].astype(str).str.strip()
    return catalog


def run_cleaning() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Execute all ten cleaning challenges plus residual missing-value handling."""
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    metrics: dict[str, Any] = {}

    print("Loading raw transactions...")
    df = load_raw_transactions()
    metrics["rows_before"] = int(len(df))
    metrics["columns_before"] = list(df.columns)

    print("Q1 dates...")
    df = clean_order_dates(df, metrics)
    print("Q2 + Q9 prices / outliers...")
    df = clean_original_price(df, metrics)
    print("Q3 ratings...")
    df = clean_ratings(df, metrics)
    print("Q4 cities...")
    df = clean_cities(df, metrics)
    print("Q5 booleans...")
    df = clean_booleans(df, metrics)
    print("Q6 categories...")
    df = clean_categories(df, metrics)
    print("Q7 delivery days...")
    df = clean_delivery_days(df, metrics)
    print("Q8 duplicates...")
    df = handle_duplicates(df, metrics)
    print("Q10 payments...")
    df = clean_payments(df, metrics)
    print("Remaining fields...")
    df = clean_remaining_fields(df, metrics)

    drop_cols = [c for c in ["source_file"] if c in df.columns]
    df = df.drop(columns=drop_cols)
    df = df.sort_values(["order_date", "transaction_id"]).reset_index(drop=True)

    catalog = load_catalog()
    metrics["rows_after"] = int(len(df))
    metrics["catalog_rows"] = int(len(catalog))
    metrics["date_min"] = str(df["order_date"].min().date())
    metrics["date_max"] = str(df["order_date"].max().date())
    metrics["revenue_inr"] = float(df["final_amount_inr"].sum())

    cleaned_path = CLEANED_DIR / "transactions_cleaned.parquet"
    catalog_path = CLEANED_DIR / "products_catalog_cleaned.parquet"
    csv_path = CLEANED_DIR / "transactions_cleaned.csv"
    df.to_parquet(cleaned_path, index=False)
    catalog.to_parquet(catalog_path, index=False)
    df.to_csv(csv_path, index=False)
    catalog.to_csv(CLEANED_DIR / "products_catalog_cleaned.csv", index=False)

    metrics_path = REPORTS_DIR / "cleaning_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, default=str), encoding="utf-8")
    print(f"Cleaned {metrics['rows_after']:,} rows → {cleaned_path}")
    return df, catalog, metrics


if __name__ == "__main__":
    run_cleaning()
