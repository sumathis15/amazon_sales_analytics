# Data Cleaning Report

All counts below were computed from the raw year files and re-checked on `data/cleaned/transactions_cleaned.parquet`.

- Rows in: **1,127,609**
- Rows out: **1,121,999**
- Date span: **2015-01-01 → 2025-12-31**
- Gross merchandise (final_amount_inr): **₹76,498,307,663.72**

## Question 1 — order_date formats

**Asked:** Standardise DD/MM/YYYY, DD-MM-YY, YYYY-MM-DD and invalid dates such as 32/13/2020 to YYYY-MM-DD.

**Found in the files (not assumed):**

| Format | Rows |
| --- | ---: |
| YYYY-MM-DD | 1,019,353 |
| Slash dates mixing DD/MM/YYYY and MM/DD/YYYY | 67,893 |
| DD-MM-YYYY | 40,363 |
| DD-MM-YY | 0 |
| Invalid / unparseable | 0 |

Slash dates are mixed: `13/01/2015` is DMY while `01/17/2015` is MDY. `order_month` matched one of the two numeric parts on every slash row, so it was used as the tie-break. Dash dates were 100% DD-MM-YYYY. No `32/13/2020`-style invalid dates were present; the parser still returns NaT for those.

**After:** every `order_date` is datetime64, `order_year` / `order_month` / `order_quarter` rebuilt from the parsed date (zero mismatches on verification).

## Question 2 — original_price_inr

**Asked:** Strip ₹, Indian commas, and 'Price on Request'; keep numeric INR.

**Found:**

- Currency prefix (`₹` or `Rs`): **78,908**
- Comma grouping (including those with a currency prefix): **101,569**
- 'Price on Request' / non-numeric after stripping: **0**
- Negative sign errors: **2,792**

There were no 'Price on Request' tokens. Negatives were sign errors: `abs(original)` matched `discounted / (1 - discount%)`.

**After:** `original_price_inr` is float64, min > 0, and the discount identity holds (max relative error < 0.05%).

## Question 3 — customer ratings

**Asked:** Standardise '5.0', '4 stars', '3/5', '2.5/5.0' onto 1.0–5.0 and handle missing values.

**Found:**

- Missing / blank: **341,696** (30.3% of raw rows)
- Non-plain formats (stars or /5): **56,544**

**Strategy:** parse every format onto 1–5. Leave genuine non-response as NaN so satisfaction analysis is not invented. `customer_rating_imputed` fills those gaps with the product's median observed rating, then `product_rating`.

**After:** unique values are {3.0, 3.5, 4.0, 4.5, 5.0}; 30.30% remain NaN by design.

## Question 4 — customer_city

**Asked:** Standardise Bangalore/Bengaluru, Mumbai/Bombay, Delhi/New Delhi, typos and case.

**Found:** 50 raw spellings (whitespace, case, Bombay, Calcutta, Madras, chenai, mumba, Delhi NCR, Banglore, Bengalore).

**After:** **30** canonical cities; **4,652** rows remapped.

## Question 5 — boolean columns

**Asked:** True/False, Yes/No, 1/0, Y/N → boolean.

Raw mixes (True/TRUE/Yes/1 vs False/FALSE/No/0) were present on `is_prime_member`, `is_prime_eligible`, `is_festival_sale`. No nulls.

**After:** pandas `bool` dtypes. Festival name is NaN exactly when `is_festival_sale` is False.

## Question 6 — product categories

**Found raw counts:** Electronics 1,126,726; Electronic 229; ELECTRONICS 225; Electronics & Accessories 218; Electronicss 211.

**After:** one category, **Electronics**. Subcategories unchanged: Smartphones, Laptops, Smart Watch, Tablets, Audio, TV & Entertainment.

## Question 7 — delivery_days

**Found:** negatives (-1: 6,836), text ('Same Day', '1-2 days', 'Express'), zeros, and 15-day outliers (2,175).

**After:** integer days **1–7**. Same Day → 1, Express → 2, Standard mode 3; invalid values imputed from `delivery_type`.

## Question 8 — duplicates

**Asked:** tell genuine bulk orders from error clones.

**Found:** 0 exact-row duplicates, 0 duplicate `transaction_id`s, **5,610** extra rows sharing customer + product + date + amount. Every pair was `(TXN_…, TXN_…_DUP)` with the same quantity. Multi-unit purchases already live in `quantity` ∈ {1,2,3}.

**Action:** dropped **5,609** `_DUP` rows plus **1** leftover key clone. **1,121,999** unique transactions remain.

## Question 9 — 100x price outliers

**Found:** original prices up to ₹33,371,693 caused by missing decimal places.

- ÷100 (ratio ~100 vs expected): **2,625**
- ÷10 (ratio ~10 vs expected): **2,744**

Expected price = `discounted_price_inr / (1 - discount_percent/100)` (discounted prices were already clean).

**After:** max original price ₹420,705, matching the clean discounted-price ceiling.

## Question 10 — payment methods

**Found:** the files already use seven canonical names (UPI, COD, Credit Card, Debit Card, Net Banking, Wallet, BNPL). PhonePe/GooglePay/CC/C.O.D. aliases listed in the brief were not present; the mapper still handles them.

**Hierarchy created:** Digital Payments, Card Payments, Cash on Delivery, Bank Transfer, Buy Now Pay Later.

| Method | Orders after cleaning |
| --- | ---: |
| UPI | 382,356 |
| COD | 321,261 |
| Credit Card | 171,396 |
| Debit Card | 139,490 |
| Net Banking | 64,620 |
| Wallet | 22,678 |
| BNPL | 20,198 |

## Other missing values (approach section)

- `delivery_charges`: 89,760 missing, almost all observed values are 0 (eight rows = 40) → filled with 0.
- `customer_age_group`: 134,640 missing; 120,707 recovered from the same `customer_id` (age never changes for a customer). 13,933 left as **Unknown** because spending-tier age mix is uniform — imputing 26-35 would only add bias.
- `festival_name` empty is valid (not a festival sale).
