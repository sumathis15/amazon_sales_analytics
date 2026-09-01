"""Advanced Analytics — Questions 26–30."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.utils import inject_theme, show_chart, apply_filters, inr, kpi_row, load_customers, load_transactions, yoy_delta
from src.config import AMAZON_NAVY, AMAZON_ORANGE, PALETTE

st.set_page_config(page_title="Advanced Analytics", layout="wide")
inject_theme()
st.title("Advanced Analytics")
st.caption("Questions 26–30 · forecast, market intel, cross-sell, seasonal planning, command center")

tx = apply_filters(load_transactions())
customers = load_customers()
if tx.empty:
    st.stop()

st.header("Q26 · Predictive analytics")
monthly = tx.groupby(tx["order_date"].dt.to_period("M"))["final_amount_inr"].sum()
monthly.index = monthly.index.to_timestamp()
X = np.arange(len(monthly)).reshape(-1, 1)
model = LinearRegression().fit(X, monthly.values)
horizon = 6
future_x = np.arange(len(monthly) + horizon).reshape(-1, 1)
pred = model.predict(future_x)
idx = pd.date_range(monthly.index.min(), periods=len(pred), freq="MS")
fig = go.Figure()
fig.add_trace(go.Scatter(x=monthly.index, y=monthly.values, name="Actual", line=dict(color=AMAZON_ORANGE)))
fig.add_trace(go.Scatter(x=idx, y=pred, name="Linear forecast", line=dict(color=AMAZON_NAVY, dash="dash")))
fig.update_layout(title="Monthly revenue forecast")
show_chart(fig)

cust = customers[customers["customer_id"].isin(tx["customer_id"].unique())].copy()
snapshot = tx["order_date"].max()
cust["churned"] = (cust["last_order_date"] < snapshot - pd.Timedelta(days=365)).astype(int)
feat = cust[["recency_days", "frequency", "monetary", "avg_order_value", "is_prime_member"]].fillna(0)
if cust["churned"].nunique() == 2 and len(cust) > 200:
    scaler = StandardScaler()
    Xs = scaler.fit_transform(feat)
    clf = LogisticRegression(max_iter=400).fit(Xs, cust["churned"])
    cust["churn_prob"] = clf.predict_proba(Xs)[:, 1]
    st.caption(f"Logistic churn model (inactive 365+ days). In-sample accuracy {clf.score(Xs, cust['churned']):.3f}.")
    show_chart(px.histogram(cust, x="churn_prob", color="rfm_segment", title="Predicted churn probability"))
else:
    st.info("Not enough class variation in this filter to fit a churn model.")

st.header("Q27 · Market intelligence")
st.caption("No external competitor feed. Internal brand share, price bands and subcategory mix are the available positioning signals.")
brand = tx.groupby(["order_year", "brand"], as_index=False)["final_amount_inr"].sum()
top = tx.groupby("brand")["final_amount_inr"].sum().nlargest(6).index
show_chart(px.line(brand[brand["brand"].isin(top)], x="order_year", y="final_amount_inr", color="brand", title="Brand competitive set"))
price = tx.groupby(["subcategory", "brand"], as_index=False)["discounted_price_inr"].median()
show_chart(px.box(tx[tx["brand"].isin(top)], x="brand", y="discounted_price_inr", color="subcategory", title="Price architecture by brand"))

st.header("Q28 · Cross-sell & upsell")
pairs = (
    tx.groupby(["customer_id", "subcategory"])["transaction_id"]
    .nunique()
    .unstack(fill_value=0)
)
# association: P(B|A) among customers
subs = [c for c in pairs.columns]
records = []
n = len(pairs)
for a in subs:
    buyers_a = pairs[a] > 0
    for b in subs:
        if a == b:
            continue
        both = ((pairs[a] > 0) & (pairs[b] > 0)).sum()
        support = both / n
        conf = both / buyers_a.sum() if buyers_a.sum() else 0
        records.append({"from": a, "to": b, "support": support, "confidence": conf})
assoc = pd.DataFrame(records).sort_values("confidence", ascending=False)
show_chart(px.density_heatmap(assoc, x="to", y="from", z="confidence", title="P(buy to | bought from)"))
st.dataframe(assoc.head(12), width="stretch")

st.header("Q29 · Seasonal planning")
month_cat = tx.groupby(["order_month", "subcategory"], as_index=False)["quantity"].sum()
show_chart(px.density_heatmap(month_cat, x="order_month", y="subcategory", z="quantity", title="Unit demand calendar"))
fest = tx.groupby(["order_month", "festival_name"], as_index=False)["final_amount_inr"].sum().dropna()
show_chart(px.bar(fest, x="order_month", y="final_amount_inr", color="festival_name", title="Promotional calendar · festival GMV by month"))
st.markdown(
    """
Planning notes from the demand calendar:
- Raise smartphone and laptop inventory ahead of months that historically spike (festival-heavy Q4 and Republic Day).
- Staff delivery capacity for Same Day/Express in Metro cities during those peaks.
- Time discounts where elasticity (Q10) shows unit lift without collapsing AOV.
"""
)

st.header("Q30 · Business intelligence command center")
latest = int(tx["order_year"].max())
prev = latest - 1
by_year = tx.groupby("order_year").agg(revenue=("final_amount_inr", "sum"), customers=("customer_id", "nunique"), aov=("final_amount_inr", "mean"), returns=("return_status", lambda s: (s == "Returned").mean()), delivery=("delivery_days", "mean"))
kpi_row(
    [
        ("Revenue", inr(float(tx["final_amount_inr"].sum())), yoy_delta(by_year["revenue"].get(latest, 0), by_year["revenue"].get(prev, 0))),
        ("Customers", f"{tx['customer_id'].nunique():,}", yoy_delta(by_year["customers"].get(latest, 0), by_year["customers"].get(prev, 0))),
        ("AOV", inr(float(tx["final_amount_inr"].mean()), 0), yoy_delta(by_year["aov"].get(latest, 0), by_year["aov"].get(prev, 0))),
        ("Return rate", f"{(tx['return_status']=='Returned').mean()*100:.2f}%", None),
        ("Avg delivery days", f"{tx['delivery_days'].mean():.2f}", None),
    ]
)
alerts = []
if by_year["revenue"].get(latest, 0) < by_year["revenue"].get(prev, 0):
    alerts.append("Revenue down versus last year in the current filter.")
if (tx["return_status"] == "Returned").mean() > 0.08:
    alerts.append("Return rate above 8%.")
if tx["delivery_days"].mean() > 4:
    alerts.append("Average delivery slower than 4 days.")
if (cust["churned"].mean() if "churned" in cust.columns else 0) > 0.35:
    alerts.append("More than 35% of customers look churned (365+ days inactive).")
if alerts:
    for a in alerts:
        st.error(a)
else:
    st.success("No automated threshold alerts for the current filter.")
c1, c2 = st.columns(2)
with c1:
    show_chart(px.line(by_year.reset_index(), x="order_year", y="revenue", markers=True, title="Command center · revenue"))
with c2:
    mix = tx.groupby("subcategory", as_index=False)["final_amount_inr"].sum()
    show_chart(px.pie(mix, names="subcategory", values="final_amount_inr", title="Command center · mix", hole=0.45))
