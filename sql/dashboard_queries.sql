-- KPI: yearly revenue and orders
SELECT order_year,
       SUM(final_amount_inr) AS revenue,
       COUNT(*) AS orders,
       COUNT(DISTINCT customer_id) AS active_customers,
       AVG(final_amount_inr) AS aov
FROM transactions
GROUP BY order_year
ORDER BY order_year;

-- Category (subcategory) contribution
SELECT subcategory,
       SUM(final_amount_inr) AS revenue,
       SUM(quantity) AS units,
       COUNT(DISTINCT customer_id) AS customers
FROM transactions
GROUP BY subcategory
ORDER BY revenue DESC;

-- Geographic revenue
SELECT customer_state, customer_tier,
       SUM(final_amount_inr) AS revenue,
       COUNT(*) AS orders
FROM transactions
GROUP BY customer_state, customer_tier
ORDER BY revenue DESC;

-- Prime vs non-Prime
SELECT is_prime_member,
       COUNT(*) AS orders,
       SUM(final_amount_inr) AS revenue,
       AVG(final_amount_inr) AS aov,
       AVG(delivery_days) AS avg_delivery_days
FROM transactions
GROUP BY is_prime_member;

-- RFM segment value
SELECT rfm_segment,
       COUNT(*) AS customers,
       SUM(monetary) AS revenue,
       AVG(clv) AS avg_clv
FROM customers
GROUP BY rfm_segment
ORDER BY revenue DESC;

-- Multi-table: brand x year
SELECT t.order_year, t.brand,
       SUM(t.final_amount_inr) AS revenue,
       SUM(t.quantity) AS units
FROM transactions t
JOIN products p ON t.product_id = p.product_id
GROUP BY t.order_year, t.brand
ORDER BY t.order_year, revenue DESC;
