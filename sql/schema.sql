DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS time_dimension;

CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT,
    category TEXT,
    subcategory TEXT,
    brand TEXT,
    base_price_2015 REAL,
    weight_kg REAL,
    rating REAL,
    is_prime_eligible INTEGER,
    launch_year INTEGER,
    model TEXT,
    units_sold INTEGER,
    orders INTEGER,
    revenue REAL,
    avg_discount REAL,
    avg_customer_rating REAL,
    return_rate REAL,
    first_sold TEXT,
    last_sold TEXT
);

CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    customer_city TEXT,
    customer_state TEXT,
    customer_tier TEXT,
    customer_spending_tier TEXT,
    customer_age_group TEXT,
    is_prime_member INTEGER,
    first_order_date TEXT,
    last_order_date TEXT,
    frequency INTEGER,
    monetary REAL,
    units INTEGER,
    avg_order_value REAL,
    avg_rating REAL,
    return_rate REAL,
    recency_days INTEGER,
    tenure_days INTEGER,
    acquisition_year INTEGER,
    r_score INTEGER,
    f_score INTEGER,
    m_score INTEGER,
    rfm_segment TEXT,
    rfm_action TEXT,
    clv REAL
);

CREATE TABLE time_dimension (
    date TEXT PRIMARY KEY,
    year INTEGER,
    quarter INTEGER,
    month INTEGER,
    month_name TEXT,
    week INTEGER,
    day INTEGER,
    day_of_week INTEGER,
    day_name TEXT,
    is_weekend INTEGER,
    year_month TEXT,
    year_quarter TEXT,
    festival_name TEXT,
    is_festival INTEGER
);

CREATE TABLE transactions (
    transaction_id TEXT PRIMARY KEY,
    order_date TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    product_name TEXT,
    category TEXT,
    subcategory TEXT,
    brand TEXT,
    original_price_inr REAL,
    discount_percent REAL,
    discounted_price_inr REAL,
    quantity INTEGER,
    subtotal_inr REAL,
    delivery_charges REAL,
    final_amount_inr REAL,
    customer_city TEXT,
    customer_state TEXT,
    customer_tier TEXT,
    customer_spending_tier TEXT,
    customer_age_group TEXT,
    payment_method TEXT,
    payment_method_group TEXT,
    delivery_days INTEGER,
    delivery_type TEXT,
    is_prime_member INTEGER,
    is_prime_eligible INTEGER,
    is_festival_sale INTEGER,
    festival_name TEXT,
    customer_rating REAL,
    customer_rating_imputed REAL,
    return_status TEXT,
    order_month INTEGER,
    order_year INTEGER,
    order_quarter INTEGER,
    order_day INTEGER,
    product_weight_kg REAL,
    product_rating REAL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (order_date) REFERENCES time_dimension(date)
);

CREATE INDEX idx_txn_date ON transactions(order_date);
CREATE INDEX idx_txn_customer ON transactions(customer_id);
CREATE INDEX idx_txn_product ON transactions(product_id);
CREATE INDEX idx_txn_year ON transactions(order_year);
CREATE INDEX idx_txn_category ON transactions(category);
CREATE INDEX idx_txn_subcategory ON transactions(subcategory);
CREATE INDEX idx_txn_city ON transactions(customer_city);
CREATE INDEX idx_txn_state ON transactions(customer_state);
CREATE INDEX idx_txn_payment ON transactions(payment_method);
CREATE INDEX idx_txn_prime ON transactions(is_prime_member);
CREATE INDEX idx_txn_festival ON transactions(is_festival_sale);
CREATE INDEX idx_txn_brand ON transactions(brand);
CREATE INDEX idx_cust_segment ON customers(rfm_segment);
CREATE INDEX idx_cust_city ON customers(customer_city);
CREATE INDEX idx_prod_brand ON products(brand);
CREATE INDEX idx_prod_subcat ON products(subcategory);
