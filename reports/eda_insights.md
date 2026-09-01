# EDA Insights and Business Recommendations

Figures live in `reports/eda_figures/`. Every number was written by `src/eda.py` from the cleaned parquet.

## Question 1 — Yearly revenue trend

CAGR 2015–2025: **6.0%**. Fastest growth year: **2016 (+68.0%)**. Total GMV: **₹76,498,307,664**.

| Year | Revenue (INR) | Orders | YoY |
| --- | ---: | ---: | ---: |
| 2015 | ₹2,130,499,205 | 33,000 |  |
| 2016 | ₹3,579,914,356 | 54,999 | +68.0% |
| 2017 | ₹5,479,954,036 | 77,000 | +53.1% |
| 2018 | ₹7,213,275,820 | 99,000 | +31.6% |
| 2019 | ₹8,563,454,684 | 121,000 | +18.7% |
| 2020 | ₹11,813,639,060 | 143,000 | +38.0% |
| 2021 | ₹10,934,111,732 | 137,500 | -7.4% |
| 2022 | ₹8,489,730,079 | 132,000 | -22.4% |
| 2023 | ₹7,673,823,148 | 126,500 | -9.6% |
| 2024 | ₹6,788,208,374 | 121,000 | -11.5% |
| 2025 | ₹3,831,697,167 | 77,000 | -43.6% |

**Recommendation:** treat the post-peak years as a maturity phase — grow AOV and Prime mix rather than relying on the early double-digit volume expansion.

## Question 2 — Seasonality

Peak calendar month: **12** (₹10,014,230,747 across the decade). Heatmaps show festival-heavy late-year density.

**Recommendation:** lock inventory and Same Day capacity before the peak month; run test campaigns in the weakest month to flatten the trough.

## Question 3 — RFM segmentation

| Segment | Customers | Historical revenue |
| --- | ---: | ---: |
| Loyal Customers | 65,426 | ₹18,344,715,250 |
| Lost | 61,114 | ₹4,188,275,666 |
| At Risk | 43,945 | ₹9,927,729,864 |
| Champions | 41,020 | ₹17,900,812,186 |
| Cannot Lose Them | 37,406 | ₹17,963,829,753 |
| Hibernating | 30,270 | ₹2,310,272,901 |
| About to Sleep | 25,282 | ₹1,689,391,732 |
| Promising | 20,499 | ₹815,822,116 |
| New Customers | 12,577 | ₹495,587,132 |
| Need Attention | 10,701 | ₹1,638,944,623 |
| Potential Loyalists | 6,729 | ₹1,222,926,442 |

**Recommendation:** protect Champions/Loyal with Prime-only drops; run win-back on At Risk / Cannot Lose Them; do not overspend on Lost.

## Question 4 — Payment evolution

UPI share of orders: **0.0% (2015) → 60.2% (2025)**. COD: **75.3% → 8.1%**.

**Recommendation:** keep UPI as the default checkout; use COD fees or prepaid discounts where COD remains high.

## Question 5 — Category performance

Everything is Electronics. Subcategory GMV / share / CAGR 2015–2025:

| Subcategory | GMV (₹ Cr) | Share | CAGR |
| --- | ---: | ---: | ---: |
| Smartphones | 5,587.1 | 73.0% | 7.2% |
| Laptops | 935.2 | 12.2% | 2.8% |
| Tablets | 505.9 | 6.6% | 1.7% |
| Smart Watch | 319.8 | 4.2% | 4.1% |
| TV & Entertainment | 191.3 | 2.5% | 2.9% |
| Audio | 110.6 | 1.4% | 17.3% |

**Recommendation:** smartphones fund the P&L; audio is the fastest-growing attach category. Use the Q17 transition matrix (phones ↔ watches/laptops) for bundles.

## Question 6 — Prime impact

AOV Prime **₹77,020** vs non-Prime **₹59,428** (+29.6%). Prime revenue share **43.7%**. Orders per customer on Prime-flagged baskets **2.66** vs **3.58** non-Prime — Prime is an AOV / mix effect, not a frequency effect on this split (membership is a line-level flag and grew in the later, lower-volume years).

**Recommendation:** sell Prime on basket size and faster delivery, not on “you will order more often,” unless a true subscriber panel is built.

## Question 7 — Geography

Tier revenue: Metro ₹42,207,939,247, Tier1 ₹22,076,617,621, Tier2 ₹9,901,669,735, Rural ₹2,312,081,060.

Top city: Mumbai (₹10,599,286,716).

**Recommendation:** Metro still concentrates GMV; Tier2/Rural is the expansion wedge if delivery days stay inside SLA (Q11).

## Question 8 — Festival impact

Festival order share **31.0%**. Campaign GMV (₹ Cr): Back to School 405.3, Diwali Sale 394.0, Amazon Great Indian Festival 250.6, Summer Sale 210.9, Holi 187.6, Republic Day 95.5, Valentine 66.2, Prime Day 43.3.

Diwali daily run-rate in the 14 days before the labelled window is *higher* than the during-window daily rate (e.g. 2017: ₹2.06 Cr/day before vs ₹1.42 Cr/day during). The labelled festival period is long, so the spike is in duration and total GMV, not in daily intensity. December still holds **13.1%** of decade GMV (Q2).

**Recommendation:** measure incrementality as during minus the 14-day pre-window, not vs a quiet month — and do not assume the festival tag equals a higher daily run-rate.

## Question 9 — Age groups

GMV ₹ Cr: 26-35 **2,655**, 18-25 **2,413**, 36-45 **1,512**, 46-55 **751**, 55+ **227**, Unknown **92**. AOV is almost flat (~₹67.7k–₹68.3k). Age shifts mix more than it shifts ticket size.

## Question 10 — Price vs demand

SKU-level corr(price, units) **−0.13**; corr(price, revenue) **+0.33**; corr(discount, units) **+0.02**. Demand is not a simple downward price slope: mix (phones vs audio) dominates. Discount % barely moves units at SKU grain.

## Question 11 — Delivery

Average **3.31** days, median **3**. Defined SLA (Same Day ≤1, Express ≤2, Standard ≤7) is **100%** because Standard was capped at 7 days in cleaning — treat that as a tautology, not an ops trophy. Use average days by tier and the rating-vs-speed curve instead; ratings rise as days fall.

## Question 12 — Returns

Return rate **7.02%**, cancel rate **2.31%**. Return rate by subcategory: Audio 8.01%, Smart Watch 7.37%, Tablets 7.00%, Smartphones 6.96%, Laptops 6.89%, TV & Entertainment 5.83%. Target QC on Audio/wearables, not a blunt sitewide policy.

## Question 13 — Brands

Decade GMV ₹ Cr: Samsung 2,052, Apple 1,624, OnePlus 1,226, Xiaomi 542, Realme 300, Vivo 234, Oppo 226, Lenovo 208.

Samsung share **31.1% → 26.7%** (2015→2025); Apple **19.8% → 21.7%**; Realme **0.1% → 5.0%**.

## Question 14 — CLV and cohorts

Median CLV **₹797,808**, mean **₹1,476,215**. Year-1 retention collapses for later cohorts: 2015 **82.4%**, 2016 **51.8%**, 2020 **16.9%**, 2024 **8.4%** — later vintages have had less time and the base shrank after 2020.

## Question 15 — Discounts

Average discount **17.4%**. Orders by band: 0% **503,280**; 0–10 **53,771**; 10–20 **139,743**; 20–30 **172,079**; 30–50 **126,337**; 50+ **126,789**. A large full-price core sits next to a heavy 20%+ promotional tail.

## Question 16 — Ratings vs sales

Mean product rating **3.98**, mean customer rating **4.31**. Corr(rating, units) **0.130**, corr(rating, revenue) **0.127**.

## Question 17 — Customer journey

One-time customers **25.9%**. 5+ order loyalists **21.1%**. Mean orders/customer **3.16**. Top subcategory transitions: [['Smartphones→Smartphones', 411445], ['Laptops→Smartphones', 44493], ['Smartphones→Laptops', 43361], ['Smart Watch→Smartphones', 37537], ['Smartphones→Smart Watch', 37013]].

## Question 18 — Product lifecycle

Smartphone mix **65.8% → 73.3%** of GMV (2015→2025); laptops **15.1% → 11.0%**; tablets **8.8% → 5.8%**; audio **0.8% → 2.3%**. New SKUs should be judged on first-year velocity (dashboard Q20), not lifetime totals.

## Question 19 — Competitive pricing

Box plots show brand price architecture; Apple/Samsung sit higher, Xiaomi/Realme occupy volume. Size in the scatter is rating.

## Question 20 — Business health

Linear slope **₹298,584,898** per year. 2025 active customers **38,826**. Latest return rate **7.08%**.

**Executive read:** the decade converted a COD, metro, smartphone business into a UPI-heavy, Prime-tilted one. Growth is now mix and retention, not just new logos.
