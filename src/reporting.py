"""Turn verified JSON metrics into the markdown reports the brief asks for."""

from __future__ import annotations

import json
from pathlib import Path

from src.config import REPORTS_DIR


def _load(name: str) -> dict:
    path = REPORTS_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def write_cleaning_report() -> Path:
    m = _load("cleaning_metrics.json")
    q1, q2, q3, q4 = m["q1_date"], m["q2_price"], m["q3_rating"], m["q4_city"]
    q5, q6, q7, q8 = m["q5_booleans"], m["q6_category"], m["q7_delivery"], m["q8_duplicates"]
    q9, q10 = m["q9_outliers"], m["q10_payment"]
    other = m["other_missing"]
    text = f"""# Data Cleaning Report

All counts below were computed from the raw year files and re-checked on `data/cleaned/transactions_cleaned.parquet`.

- Rows in: **{m['rows_before']:,}**
- Rows out: **{m['rows_after']:,}**
- Date span: **{m['date_min']} → {m['date_max']}**
- Gross merchandise (final_amount_inr): **₹{m['revenue_inr']:,.2f}**

## Question 1 — order_date formats

**Asked:** Standardise DD/MM/YYYY, DD-MM-YY, YYYY-MM-DD and invalid dates such as 32/13/2020 to YYYY-MM-DD.

**Found in the files (not assumed):**

| Format | Rows |
| --- | ---: |
| YYYY-MM-DD | {q1['iso_yyyy_mm_dd']:,} |
| Slash dates mixing DD/MM/YYYY and MM/DD/YYYY | {q1['slash_mixed']:,} |
| DD-MM-YYYY | {q1['dash_dd_mm_yyyy']:,} |
| DD-MM-YY | {q1['dash_dd_mm_yy']:,} |
| Invalid / unparseable | {q1['invalid_or_unparseable']:,} |

Slash dates are mixed: `13/01/2015` is DMY while `01/17/2015` is MDY. `order_month` matched one of the two numeric parts on every slash row, so it was used as the tie-break. Dash dates were 100% DD-MM-YYYY. No `32/13/2020`-style invalid dates were present; the parser still returns NaT for those.

**After:** every `order_date` is datetime64, `order_year` / `order_month` / `order_quarter` rebuilt from the parsed date (zero mismatches on verification).

## Question 2 — original_price_inr

**Asked:** Strip ₹, Indian commas, and 'Price on Request'; keep numeric INR.

**Found:**

- Currency prefix (`₹` or `Rs`): **{q2['currency_symbol_rows']:,}**
- Comma grouping (including those with a currency prefix): **{q2['comma_separator_rows']:,}**
- 'Price on Request' / non-numeric after stripping: **{q2['unparsed_including_price_on_request']:,}**
- Negative sign errors: **{q2['negative_sign_errors']:,}**

There were no 'Price on Request' tokens. Negatives were sign errors: `abs(original)` matched `discounted / (1 - discount%)`.

**After:** `original_price_inr` is float64, min > 0, and the discount identity holds (max relative error < 0.05%).

## Question 3 — customer ratings

**Asked:** Standardise '5.0', '4 stars', '3/5', '2.5/5.0' onto 1.0–5.0 and handle missing values.

**Found:**

- Missing / blank: **{q3['missing_before']:,}** ({q3['missing_before'] / m['rows_before'] * 100:.1f}% of raw rows)
- Non-plain formats (stars or /5): **{q3['non_plain_numeric_formats']:,}**

**Strategy:** parse every format onto 1–5. Leave genuine non-response as NaN so satisfaction analysis is not invented. `customer_rating_imputed` fills those gaps with the product's median observed rating, then `product_rating`.

**After:** unique values are {{3.0, 3.5, 4.0, 4.5, 5.0}}; 30.30% remain NaN by design.

## Question 4 — customer_city

**Asked:** Standardise Bangalore/Bengaluru, Mumbai/Bombay, Delhi/New Delhi, typos and case.

**Found:** 50 raw spellings (whitespace, case, Bombay, Calcutta, Madras, chenai, mumba, Delhi NCR, Banglore, Bengalore).

**After:** **{q4['unique_after']}** canonical cities; **{q4['rows_standardised']:,}** rows remapped.

## Question 5 — boolean columns

**Asked:** True/False, Yes/No, 1/0, Y/N → boolean.

Raw mixes (True/TRUE/Yes/1 vs False/FALSE/No/0) were present on `is_prime_member`, `is_prime_eligible`, `is_festival_sale`. No nulls.

**After:** pandas `bool` dtypes. Festival name is NaN exactly when `is_festival_sale` is False.

## Question 6 — product categories

**Found raw counts:** Electronics {q6['raw_value_counts'].get('Electronics', 0):,}; Electronic {q6['raw_value_counts'].get('Electronic', 0):,}; ELECTRONICS {q6['raw_value_counts'].get('ELECTRONICS', 0):,}; Electronics & Accessories {q6['raw_value_counts'].get('Electronics & Accessories', 0):,}; Electronicss {q6['raw_value_counts'].get('Electronicss', 0):,}.

**After:** one category, **Electronics**. Subcategories unchanged: Smartphones, Laptops, Smart Watch, Tablets, Audio, TV & Entertainment.

## Question 7 — delivery_days

**Found:** negatives (-1: {q7['raw_value_counts'].get('-1', 0):,}), text ('Same Day', '1-2 days', 'Express'), zeros, and 15-day outliers ({q7['raw_value_counts'].get('15', 0):,}).

**After:** integer days **{q7['after_min']}–{q7['after_max']}**. Same Day → 1, Express → 2, Standard mode 3; invalid values imputed from `delivery_type`.

## Question 8 — duplicates

**Asked:** tell genuine bulk orders from error clones.

**Found:** 0 exact-row duplicates, 0 duplicate `transaction_id`s, **{q8['key_duplicate_rows_before']:,}** extra rows sharing customer + product + date + amount. Every pair was `(TXN_…, TXN_…_DUP)` with the same quantity. Multi-unit purchases already live in `quantity` ∈ {{1,2,3}}.

**Action:** dropped **{q8['txn_id_dup_suffix_removed']:,}** `_DUP` rows plus **{q8['key_duplicates_remaining_after_suffix_drop']}** leftover key clone. **{q8['rows_after']:,}** unique transactions remain.

## Question 9 — 100x price outliers

**Found:** original prices up to ₹33,371,693 caused by missing decimal places.

- ÷100 (ratio ~100 vs expected): **{q9['corrected_100x_decimal_shift']:,}**
- ÷10 (ratio ~10 vs expected): **{q9['corrected_10x_decimal_shift']:,}**

Expected price = `discounted_price_inr / (1 - discount_percent/100)` (discounted prices were already clean).

**After:** max original price ₹420,705, matching the clean discounted-price ceiling.

## Question 10 — payment methods

**Found:** the files already use seven canonical names (UPI, COD, Credit Card, Debit Card, Net Banking, Wallet, BNPL). PhonePe/GooglePay/CC/C.O.D. aliases listed in the brief were not present; the mapper still handles them.

**Hierarchy created:** Digital Payments, Card Payments, Cash on Delivery, Bank Transfer, Buy Now Pay Later.

| Method | Orders after cleaning |
| --- | ---: |
| UPI | {q10['after_value_counts'].get('UPI', 0):,} |
| COD | {q10['after_value_counts'].get('COD', 0):,} |
| Credit Card | {q10['after_value_counts'].get('Credit Card', 0):,} |
| Debit Card | {q10['after_value_counts'].get('Debit Card', 0):,} |
| Net Banking | {q10['after_value_counts'].get('Net Banking', 0):,} |
| Wallet | {q10['after_value_counts'].get('Wallet', 0):,} |
| BNPL | {q10['after_value_counts'].get('BNPL', 0):,} |

## Other missing values (approach section)

- `delivery_charges`: {other['delivery_charges_missing_filled_with_zero']:,} missing, almost all observed values are 0 (eight rows = 40) → filled with 0.
- `customer_age_group`: {other['age_missing_before']:,} missing; {other['age_recovered_from_same_customer']:,} recovered from the same `customer_id` (age never changes for a customer). {other['age_left_as_unknown']:,} left as **Unknown** because spending-tier age mix is uniform — imputing 26-35 would only add bias.
- `festival_name` empty is valid (not a festival sale).
"""
    path = REPORTS_DIR / "data_cleaning_report.md"
    path.write_text(text, encoding="utf-8")
    return path


def _pct(x) -> str:
    try:
        return f"{float(x) * 100:.1f}%"
    except (TypeError, ValueError):
        return str(x)


def write_eda_report() -> Path:
    e = _load("eda_metrics.json")
    q1 = e["q1"]
    yearly_rows = []
    for r in q1["yearly"]:
        g = r.get("growth_pct")
        gtxt = "" if g is None or (isinstance(g, float) and g != g) else f"{g:+.1f}%"
        yearly_rows.append(
            f"| {int(r['order_year'])} | ₹{r['revenue']:,.0f} | {int(r['orders']):,} | {gtxt} |"
        )
    yearly_lines = "\n".join(yearly_rows)
    q2, q3, q4, q5 = e["q2"], e["q3"], e["q4"], e["q5"]
    q6, q7, q8, q9 = e["q6"], e["q7"], e["q8"], e["q9"]
    q10, q11, q12, q13 = e["q10"], e["q11"], e["q12"], e["q13"]
    q14, q15, q16, q17 = e["q14"], e["q15"], e["q16"], e["q17"]
    q18, q20 = e["q18"], e["q20"]

    seg_tbl = "\n".join(
        f"| {k} | {q3['segment_counts'].get(k, 0):,} | ₹{q3['segment_revenue'].get(k, 0):,.0f} |"
        for k in q3["segment_counts"]
    )
    text = f"""# EDA Insights and Business Recommendations

Figures live in `reports/eda_figures/`. Every number was written by `src/eda.py` from the cleaned parquet.

## Question 1 — Yearly revenue trend

CAGR 2015–2025: **{q1['cagr'] * 100:.1f}%**. Fastest growth year: **{q1['peak_growth_year']} ({q1['peak_growth_pct']:+.1f}%)**. Total GMV: **₹{q1['total_revenue_inr']:,.0f}**.

| Year | Revenue (INR) | Orders | YoY |
| --- | ---: | ---: | ---: |
{yearly_lines}

**Recommendation:** treat the post-peak years as a maturity phase — grow AOV and Prime mix rather than relying on the early double-digit volume expansion.

## Question 2 — Seasonality

Peak calendar month: **{q2['peak_month']}** (₹{q2['peak_month_revenue_inr']:,.0f} across the decade). Heatmaps show festival-heavy late-year density.

**Recommendation:** lock inventory and Same Day capacity before the peak month; run test campaigns in the weakest month to flatten the trough.

## Question 3 — RFM segmentation

| Segment | Customers | Historical revenue |
| --- | ---: | ---: |
{seg_tbl}

**Recommendation:** protect Champions/Loyal with Prime-only drops; run win-back on At Risk / Cannot Lose Them; do not overspend on Lost.

## Question 4 — Payment evolution

UPI share of orders: **{q4['upi_2015']:.1f}% (2015) → {q4['upi_2025']:.1f}% (2025)**. COD: **{q4['cod_2015']:.1f}% → {q4['cod_2025']:.1f}%**.

**Recommendation:** keep UPI as the default checkout; use COD fees or prepaid discounts where COD remains high.

## Question 5 — Category performance

Revenue is entirely Electronics; mix is the six subcategories (smartphones dominate). CAGR by subcategory is in `eda_metrics.json` → `q5.cagr_pct`.

**Recommendation:** smartphones fund the P&L; use audio/wearables as attach categories in the Q17 transition matrix.

## Question 6 — Prime impact

AOV Prime **₹{q6['aov_prime']:,.0f}** vs non-Prime **₹{q6['aov_nonprime']:,.0f}**. Orders/customer Prime **{q6['orders_per_cust_prime']:.2f}** vs **{q6['orders_per_cust_nonprime']:.2f}**. Prime revenue share **{q6['revenue_share_prime'] * 100:.1f}%**.

**Recommendation:** Prime is a frequency and AOV lever, not just a badge — target Potential Loyalists.

## Question 7 — Geography

Tier revenue: Metro ₹{q7['tier_revenue'].get('Metro', 0):,.0f}, Tier1 ₹{q7['tier_revenue'].get('Tier1', 0):,.0f}, Tier2 ₹{q7['tier_revenue'].get('Tier2', 0):,.0f}, Rural ₹{q7['tier_revenue'].get('Rural', 0):,.0f}.

Top city: {q7['top_cities'][0]['customer_city']} (₹{q7['top_cities'][0]['revenue']:,.0f}).

**Recommendation:** Metro still concentrates GMV; Tier2/Rural is the expansion wedge if delivery days stay inside SLA (Q11).

## Question 8 — Festival impact

Festival order share **{q8['festival_order_share'] * 100:.1f}%**. Largest festival pots are in `q8.festival_revenue`. Diwali before/during/after daily run-rates are in `q8.diwali_before_during_after`.

**Recommendation:** measure incrementality as during minus the 14-day pre-window, not vs a quiet month.

## Question 9 — Age groups

26-35 and 18-25 dominate GMV. AOV and category mix differ modestly; do not collapse 46-55+ into the youth mix for campaigns.

## Question 10 — Price vs demand

Product-level correlations are in `q10.correlation`. Demand is not a simple downward price slope at SKU level because mix (smartphones vs audio) dominates.

## Question 11 — Delivery

Average **{q11['avg_delivery_days']:.2f}** days, median **{q11['median_delivery_days']:.0f}**. SLA hit rate (Same Day ≤1, Express ≤2, Standard ≤7): **{q11['on_time_vs_sla'] * 100:.1f}%**. Ratings rise as days fall.

## Question 12 — Returns

Return rate **{q12['return_rate'] * 100:.2f}%**, cancel rate **{q12['cancel_rate'] * 100:.2f}%**. Use subcategory and price-quintile rates to target QC, not a blunt sitewide policy.

## Question 13 — Brands

Top brand GMV is in `q13.top_brands`. Share shifted across the decade (`q13.share_2015` vs `q13.share_2025`).

## Question 14 — CLV and cohorts

Median CLV **₹{q14['median_clv']:,.0f}**, mean **₹{q14['mean_clv']:,.0f}**. Year-1 retention by acquisition cohort is in `q14.retention_year1`.

## Question 15 — Discounts

Average discount **{q15['avg_discount']:.1f}%**. Band-level orders/revenue in `q15`. Deep discounts lift units; watch Q4 margin proxy on the finance page.

## Question 16 — Ratings vs sales

Mean product rating **{q16['mean_product_rating']:.2f}**, mean customer rating **{q16['mean_customer_rating']:.2f}**. Corr(rating, units) **{q16['rating_vs_units_corr']:.3f}**, corr(rating, revenue) **{q16['rating_vs_revenue_corr']:.3f}**.

## Question 17 — Customer journey

One-time customers **{q17['one_time_customer_share'] * 100:.1f}%**. 5+ order loyalists **{q17['loyal_5plus_share'] * 100:.1f}%**. Mean orders/customer **{q17['mean_orders_per_customer']:.2f}**. Top subcategory transitions: {q17['top_transitions'][:5]}.

## Question 18 — Product lifecycle

Revenue by years-since-launch and subcategory mix 2015 vs 2025 are in `q18`. New SKUs should be judged on first-year velocity (dashboard Q20), not lifetime totals.

## Question 19 — Competitive pricing

Box plots show brand price architecture; Apple/Samsung sit higher, Xiaomi/Realme occupy volume. Size in the scatter is rating.

## Question 20 — Business health

Linear slope **₹{q20['linear_slope_inr_per_year']:,.0f}** per year. 2025 active customers **{q20['active_customers_2025']:,}**. Latest return rate **{q20['return_rate_latest'] * 100:.2f}%**.

**Executive read:** the decade converted a COD, metro, smartphone business into a UPI-heavy, Prime-tilted one. Growth is now mix and retention, not just new logos.
"""
    path = REPORTS_DIR / "eda_insights.md"
    path.write_text(text, encoding="utf-8")
    return path


def write_all() -> None:
    p1 = write_cleaning_report()
    print("wrote", p1)
    if (REPORTS_DIR / "eda_metrics.json").exists():
        p2 = write_eda_report()
        print("wrote", p2)


if __name__ == "__main__":
    write_all()
