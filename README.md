# Amazon India: A Decade of Sales Analytics

End-to-end analytics on Amazon India transactions (2015–2025): inspect → clean (10 challenges) → EDA (20 charts) → SQLite → Streamlit (30 dashboard questions).

## Deliverables

| Item | Location |
| --- | --- |
| Cleaning (questions 1–10) | `src/cleaning.py`, Streamlit **Data Cleaning** page, `reports/data_cleaning_report.md` |
| EDA (questions 1–20) | `src/eda.py`, Streamlit **EDA** page, `reports/eda_figures/`, `reports/eda_insights.md` |
| Cleaned tables | `data/cleaned/*.parquet` |
| SQL schema + KPI queries | `sql/schema.sql`, `sql/dashboard_queries.sql` |
| Streamlit app | `dashboard/Home.py` + `dashboard/pages/` |
| Data dictionary | `docs/data_dictionary.md` |

PowerBI is not used; the brief allows Streamlit.

## Local setup

```bash
python -m pip install -r requirements.txt
streamlit run dashboard/Home.py
```

The app reads `data/cleaned/*.parquet`. To rebuild from the raw year CSVs (keep those CSVs in the project root; they are not in git):

```bash
python -m src.cleaning
python scripts/run_pipeline.py
```

Windows, if `src` is not found:

```powershell
$env:PYTHONPATH = (Get-Location).Path
```

The optional SQLite warehouse (`data/amazon_india_analytics.db`) is rebuilt by the pipeline and is not stored in git (file size).

## Streamlit Cloud

1. Open [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
2. **Create app** → this repository.
3. **Main file path:** `dashboard/Home.py`
4. Python version: **3.12** (see `runtime.txt`).
5. Deploy. First load caches the parquet warehouse and takes longer than later reruns.

No secrets are required. Sidebar filters apply on every analytics page.

## Pipeline notes

- Cleaning rules follow values actually present in the year files (`scripts/inspect_data_quality.py`), not only the examples in the brief.
- Revenue KPIs use `final_amount_inr`.
- Customer ratings that were never collected stay null. `customer_rating_imputed` is a companion fill only.
- Dashboard pages map onto the 30 dashboard questions in the brief (five per page). Cleaning and EDA questions have their own pages.

## Layout

```
src/           cleaning, dimensions, database, eda, reporting
scripts/       inspectors, verification, pipeline
dashboard/     Streamlit multipage app
sql/           schema and aggregation queries
data/cleaned/  parquet tables used by the app
reports/       metrics, write-ups, EDA figures
docs/          data dictionary
```
