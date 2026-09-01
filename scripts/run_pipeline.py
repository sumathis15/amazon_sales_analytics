"""End-to-end pipeline: dimensions → SQLite → EDA → reports.

Cleaning is a separate first step (`python -m src.cleaning`) because it is
the slowest raw I/O stage and should not be repeated unless the CSVs change.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from src.config import CLEANED_DIR
from src.database import fetch_df, load_database
from src.dimensions import run_dimensions
from src.eda import run_eda
from src.reporting import write_all


def main() -> None:
    tx = pd.read_parquet(CLEANED_DIR / "transactions_cleaned.parquet")
    catalog = pd.read_parquet(CLEANED_DIR / "products_catalog_cleaned.parquet")
    dims = run_dimensions(tx=tx, catalog=catalog)
    load_database(
        tx=tx,
        customers=dims["customers"],
        products=dims["products"],
        time_dim=dims["time_dim"],
    )
    print("Validating SQL aggregations...")
    yearly = fetch_df(
        """
        SELECT order_year,
               SUM(final_amount_inr) AS revenue,
               COUNT(*) AS orders,
               COUNT(DISTINCT customer_id) AS active_customers,
               AVG(final_amount_inr) AS aov
        FROM transactions
        GROUP BY order_year
        ORDER BY order_year
        """
    )
    print(yearly.to_string(index=False))
    run_eda(tx=tx, customers=dims["customers"], products=dims["products"])
    write_all()
    print("Pipeline finished.")


if __name__ == "__main__":
    main()
