# Data Dictionary

Source: cleaned warehouse built from `amazon_india_20{15-25}.csv` and `amazon_india_products_catalog.csv`.

## transactions (`data/cleaned/transactions_cleaned.parquet`)

| Column | Type | Description |
| --- | --- | --- |
| transaction_id | text | Unique order line id. `_DUP` clones were removed. |
| order_date | datetime | Calendar date, ISO YYYY-MM-DD after cleaning. |
| order_year, order_month, order_quarter, order_day | int | Rebuilt from `order_date`. |
| customer_id | text | Customer key. |
| product_id | text | Product key (matches catalog). |
| product_name | text | Item title. |
| category | text | Canonical category (Electronics). |
| subcategory | text | Smartphones, Laptops, Tablets, Audio, Smart Watch, TV & Entertainment. |
| brand | text | Brand name. |
| original_price_inr | float | List price in INR after symbol/comma/outlier/sign fixes. |
| discount_percent | float | 0–70 observed. |
| discounted_price_inr | float | Unit price after discount. |
| quantity | int | 1–3 units on the line. |
| subtotal_inr | float | Line subtotal. |
| delivery_charges | float | Missing values filled with 0. |
| final_amount_inr | float | Amount charged (revenue measure used everywhere). |
| customer_city | text | 30 canonical Indian cities. |
| customer_state | text | 15 states/UTs. |
| customer_tier | text | Metro / Tier1 / Tier2 / Rural. |
| customer_spending_tier | text | Budget / Standard / Premium. |
| customer_age_group | text | 18-25, 26-35, 36-45, 46-55, 55+, Unknown. |
| payment_method | text | UPI, COD, Credit Card, Debit Card, Net Banking, Wallet, BNPL. |
| payment_method_group | text | Digital Payments, Card Payments, Cash on Delivery, Bank Transfer, Buy Now Pay Later. |
| delivery_days | int | 1–7 after cleaning. |
| delivery_type | text | Same Day / Express / Standard. |
| is_prime_member | bool | Order placed as Prime. |
| is_prime_eligible | bool | SKU Prime-eligible. |
| is_festival_sale | bool | Festival campaign flag. |
| festival_name | text | Campaign name; null when not a festival sale. |
| customer_rating | float | 3.0–5.0 or null (true non-response). |
| customer_rating_imputed | float | Product-median / catalog rating fill. |
| return_status | text | Delivered / Returned / Cancelled. |
| product_weight_kg | float | Item weight. |
| product_rating | float | Catalog rating copied onto the line. |

Revenue KPIs always use `final_amount_inr`. Returned/cancelled lines stay in the table so return rates can be measured; filter `return_status = 'Delivered'` if you need recognised GMV.

## customers

One row per `customer_id`. RFM snapshot date = day after the last transaction in the warehouse.

| Column | Description |
| --- | --- |
| recency_days, frequency, monetary | RFM inputs. |
| r_score, f_score, m_score | Quintiles 1–5 (5 is best). |
| rfm_segment, rfm_action | Segment label and playbook text. |
| clv | 3-year expected value from observed AOV × orders/year, floored at historical monetary. |
| acquisition_year | Year of first order. |

## products

Catalog (2,004 SKUs) left-joined to lifetime units, revenue, return rate, first/last sold dates.

## time_dimension

One row per calendar day from 2015-01-01 to 2025-12-31 with year, quarter, month, week, weekday, weekend flag, and festival name when that date had festival sales.
