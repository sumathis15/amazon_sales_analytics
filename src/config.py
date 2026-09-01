"""Paths, constants, and lookup tables derived from inspected raw data."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT
DATA_DIR = ROOT / "data"
CLEANED_DIR = DATA_DIR / "cleaned"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "eda_figures"
SQL_DIR = ROOT / "sql"
DB_PATH = DATA_DIR / "amazon_india_analytics.db"

TRANSACTION_GLOB = "amazon_india_20*.csv"
CATALOG_FILE = "amazon_india_products_catalog.csv"

AMAZON_ORANGE = "#FF9900"
AMAZON_NAVY = "#232F3E"
AMAZON_TEAL = "#146EB4"
AMAZON_LIGHT = "#FEBD69"
PALETTE = [
    "#FF9900",
    "#232F3E",
    "#146EB4",
    "#067D62",
    "#B12704",
    "#37475A",
    "#00A8E1",
    "#ED7117",
    "#7A3E9D",
    "#2E7D32",
]

# Observed city aliases (after strip + casefold). Canonical = majority spelling.
CITY_ALIASES = {
    "mumbai": "Mumbai",
    "bombay": "Mumbai",
    "mumba": "Mumbai",
    "delhi": "Delhi",
    "new delhi": "Delhi",
    "delhi ncr": "Delhi",
    "bangalore": "Bangalore",
    "bengaluru": "Bangalore",
    "banglore": "Bangalore",
    "bengalore": "Bangalore",
    "kolkata": "Kolkata",
    "calcutta": "Kolkata",
    "chennai": "Chennai",
    "madras": "Chennai",
    "chenai": "Chennai",
    "pune": "Pune",
    "ahmedabad": "Ahmedabad",
    "hyderabad": "Hyderabad",
    "jaipur": "Jaipur",
    "surat": "Surat",
    "nagpur": "Nagpur",
    "kanpur": "Kanpur",
    "lucknow": "Lucknow",
    "indore": "Indore",
    "coimbatore": "Coimbatore",
    "kochi": "Kochi",
    "visakhapatnam": "Visakhapatnam",
    "patna": "Patna",
    "vadodara": "Vadodara",
    "bhubaneswar": "Bhubaneswar",
    "chandigarh": "Chandigarh",
    "ludhiana": "Ludhiana",
    "saharanpur": "Saharanpur",
    "meerut": "Meerut",
    "bareilly": "Bareilly",
    "aligarh": "Aligarh",
    "allahabad": "Allahabad",
    "varanasi": "Varanasi",
    "gorakhpur": "Gorakhpur",
    "moradabad": "Moradabad",
}

CITY_COORDS = {
    "Mumbai": (19.0760, 72.8777),
    "Delhi": (28.6139, 77.2090),
    "Bangalore": (12.9716, 77.5946),
    "Chennai": (13.0827, 80.2707),
    "Pune": (18.5204, 73.8567),
    "Kolkata": (22.5726, 88.3639),
    "Ahmedabad": (23.0225, 72.5714),
    "Hyderabad": (17.3850, 78.4867),
    "Jaipur": (26.9124, 75.7873),
    "Surat": (21.1702, 72.8311),
    "Nagpur": (21.1458, 79.0882),
    "Kanpur": (26.4499, 80.3319),
    "Lucknow": (26.8467, 80.9462),
    "Indore": (22.7196, 75.8577),
    "Coimbatore": (11.0168, 76.9558),
    "Kochi": (9.9312, 76.2673),
    "Visakhapatnam": (17.6868, 83.2185),
    "Patna": (25.5941, 85.1376),
    "Vadodara": (22.3072, 73.1812),
    "Bhubaneswar": (20.2961, 85.8245),
    "Chandigarh": (30.7333, 76.7794),
    "Ludhiana": (30.9010, 75.8573),
    "Saharanpur": (29.9680, 77.5552),
    "Meerut": (28.9845, 77.7064),
    "Bareilly": (28.3670, 79.4304),
    "Aligarh": (27.8974, 78.0880),
    "Allahabad": (25.4358, 81.8463),
    "Varanasi": (25.3176, 82.9739),
    "Gorakhpur": (26.7606, 83.3732),
    "Moradabad": (28.8386, 78.7733),
}

CATEGORY_ALIASES = {
    "electronics": "Electronics",
    "electronic": "Electronics",
    "electronics & accessories": "Electronics",
    "electronicss": "Electronics",
}

TRUE_VALUES = {"true", "yes", "1", "y", "t"}
FALSE_VALUES = {"false", "no", "0", "n", "f"}

PAYMENT_ALIASES = {
    "upi": "UPI",
    "phonepe": "UPI",
    "phone pe": "UPI",
    "googlepay": "UPI",
    "google pay": "UPI",
    "gpay": "UPI",
    "g pay": "UPI",
    "credit card": "Credit Card",
    "credit_card": "Credit Card",
    "creditcard": "Credit Card",
    "cc": "Credit Card",
    "debit card": "Debit Card",
    "debit_card": "Debit Card",
    "debitcard": "Debit Card",
    "dc": "Debit Card",
    "cod": "COD",
    "cash on delivery": "COD",
    "c.o.d": "COD",
    "c.o.d.": "COD",
    "cashondelivery": "COD",
    "net banking": "Net Banking",
    "net_banking": "Net Banking",
    "netbanking": "Net Banking",
    "nb": "Net Banking",
    "wallet": "Wallet",
    "amazon pay": "Wallet",
    "amazonpay": "Wallet",
    "bnpl": "BNPL",
    "buy now pay later": "BNPL",
    "emi": "BNPL",
}

PAYMENT_HIERARCHY = {
    "UPI": "Digital Payments",
    "Wallet": "Digital Payments",
    "Credit Card": "Card Payments",
    "Debit Card": "Card Payments",
    "Net Banking": "Bank Transfer",
    "BNPL": "Buy Now Pay Later",
    "COD": "Cash on Delivery",
}

DELIVERY_TYPE_DAYS = {
    "Same Day": 1,
    "Express": 2,
    "Standard": 3,
}

RFM_SEGMENT_MAP = {
    "Champions": "Recent, frequent, high spend — reward and retain",
    "Loyal Customers": "Buy often and spend well — upsell and loyalty offers",
    "Potential Loyalists": "Recent with growing frequency — membership and bundles",
    "New Customers": "Recent but low frequency — onboarding and first-repeat offers",
    "Promising": "Recent, low spend — category education and discounts",
    "Need Attention": "Above-average but fading — win-back campaigns",
    "About to Sleep": "Slipping recency and frequency — reactivation",
    "At Risk": "Were valuable, now stale — personalised win-back",
    "Cannot Lose Them": "High spend, low recency — immediate retention",
    "Hibernating": "Low activity across RFM — low-cost reactivation or ignore",
    "Lost": "Long inactive, low value — do not over-invest",
}
