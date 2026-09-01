"""20 EDA visualizations required by the project brief."""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.gridspec import GridSpec
from sklearn.linear_model import LinearRegression

from src.config import (
    AMAZON_NAVY,
    AMAZON_ORANGE,
    CITY_COORDS,
    CLEANED_DIR,
    FIGURES_DIR,
    PALETTE,
    REPORTS_DIR,
)

warnings.filterwarnings("ignore")

INR_CR = 1e7  # 1 crore


def _inr_cr(values) -> np.ndarray:
    return np.asarray(values, dtype=float) / INR_CR


def _fmt_cr(x: float, _pos=None) -> str:
    return f"₹{x:,.1f} Cr"


def _setup_style() -> None:
    sns.set_theme(style="whitegrid", context="talk")
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": AMAZON_NAVY,
            "axes.labelcolor": AMAZON_NAVY,
            "xtick.color": AMAZON_NAVY,
            "ytick.color": AMAZON_NAVY,
            "font.size": 10,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "savefig.dpi": 140,
            "savefig.bbox": "tight",
        }
    )


def _save(fig: plt.Figure, name: str) -> Path:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURES_DIR / name
    fig.savefig(path)
    plt.close(fig)
    return path


def q1_revenue_trend(tx: pd.DataFrame, metrics: dict) -> None:
    yearly = tx.groupby("order_year", as_index=False).agg(
        revenue=("final_amount_inr", "sum"),
        orders=("transaction_id", "count"),
    )
    yearly["growth_pct"] = yearly["revenue"].pct_change() * 100
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(yearly["order_year"], _inr_cr(yearly["revenue"]), marker="o", color=AMAZON_ORANGE, lw=2.5)
    z = np.polyfit(yearly["order_year"], _inr_cr(yearly["revenue"]), 2)
    p = np.poly1d(z)
    ax.plot(yearly["order_year"], p(yearly["order_year"]), "--", color=AMAZON_NAVY, alpha=0.7, label="Trend")
    for _, row in yearly.iterrows():
        if pd.notna(row["growth_pct"]):
            ax.annotate(
                f"{row['growth_pct']:+.1f}%",
                (row["order_year"], _inr_cr(row["revenue"])),
                textcoords="offset points",
                xytext=(0, 10),
                ha="center",
                fontsize=8,
            )
    peak_idx = yearly["growth_pct"].idxmax()
    if pd.notna(yearly.loc[peak_idx, "growth_pct"]):
        ax.axvspan(yearly.loc[peak_idx, "order_year"] - 0.4, yearly.loc[peak_idx, "order_year"] + 0.4, color=AMAZON_ORANGE, alpha=0.12)
        ax.annotate(
            f"Fastest growth {int(yearly.loc[peak_idx, 'order_year'])}",
            (yearly.loc[peak_idx, "order_year"], _inr_cr(yearly.loc[peak_idx, "revenue"])),
            xytext=(20, 30),
            textcoords="offset points",
            arrowprops=dict(arrowstyle="->", color=AMAZON_NAVY),
            fontsize=9,
        )
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(_fmt_cr))
    ax.set_title("Yearly Revenue Growth, Amazon India 2015–2025")
    ax.set_xlabel("Year")
    ax.set_ylabel("Revenue")
    ax.legend()
    _save(fig, "01_revenue_trend.png")
    metrics["q1"] = {
        "yearly": yearly.to_dict(orient="records"),
        "total_revenue_inr": float(yearly["revenue"].sum()),
        "cagr": float((yearly["revenue"].iloc[-1] / yearly["revenue"].iloc[0]) ** (1 / (len(yearly) - 1)) - 1),
        "peak_growth_year": int(yearly.loc[peak_idx, "order_year"]),
        "peak_growth_pct": float(yearly.loc[peak_idx, "growth_pct"]),
    }


def q2_seasonality(tx: pd.DataFrame, metrics: dict) -> None:
    pivot = tx.pivot_table(index="order_year", columns="order_month", values="final_amount_inr", aggfunc="sum")
    fig, axes = plt.subplots(1, 2, figsize=(16, 6), gridspec_kw={"width_ratios": [1.4, 1]})
    sns.heatmap(_inr_cr(pivot), cmap="YlOrBr", ax=axes[0], cbar_kws={"label": "₹ Cr"})
    axes[0].set_title("Monthly Revenue Heatmap (₹ Cr)")
    axes[0].set_xlabel("Month")
    axes[0].set_ylabel("Year")
    monthly = tx.groupby("order_month")["final_amount_inr"].sum()
    axes[1].bar(monthly.index, _inr_cr(monthly.values), color=AMAZON_ORANGE)
    axes[1].set_title("Peak Selling Months (all years)")
    axes[1].set_xlabel("Month")
    axes[1].set_ylabel("Revenue (₹ Cr)")
    axes[1].set_xticks(range(1, 13))
    fig.tight_layout()
    _save(fig, "02_seasonality.png")
    cat_month = tx.pivot_table(index="subcategory", columns="order_month", values="final_amount_inr", aggfunc="sum")
    fig, ax = plt.subplots(figsize=(14, 5))
    sns.heatmap(_inr_cr(cat_month), cmap="YlOrBr", ax=ax, cbar_kws={"label": "₹ Cr"})
    ax.set_title("Seasonality by Subcategory")
    _save(fig, "02b_seasonality_category.png")
    metrics["q2"] = {
        "peak_month": int(monthly.idxmax()),
        "peak_month_revenue_inr": float(monthly.max()),
        "monthly_share": {int(k): float(v / monthly.sum()) for k, v in monthly.items()},
    }


def q3_rfm(customers: pd.DataFrame, metrics: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    sample = customers.sample(min(25000, len(customers)), random_state=42)
    scatter = axes[0].scatter(
        sample["recency_days"],
        sample["frequency"],
        c=np.log1p(sample["monetary"]),
        cmap="YlOrRd",
        s=12,
        alpha=0.5,
    )
    axes[0].set_xlabel("Recency (days)")
    axes[0].set_ylabel("Frequency (orders)")
    axes[0].set_title("RFM Scatter (colour = log monetary)")
    fig.colorbar(scatter, ax=axes[0], label="log(1+monetary)")
    order = customers["rfm_segment"].value_counts()
    axes[1].barh(order.index[::-1], order.values[::-1], color=AMAZON_ORANGE)
    axes[1].set_title("Customer Segment Sizes")
    axes[1].set_xlabel("Customers")
    fig.tight_layout()
    _save(fig, "03_rfm_segmentation.png")
    metrics["q3"] = {
        "segment_counts": {str(k): int(v) for k, v in order.items()},
        "segment_revenue": {
            str(k): float(v) for k, v in customers.groupby("rfm_segment")["monetary"].sum().items()
        },
    }


def q4_payment_evolution(tx: pd.DataFrame, metrics: dict) -> None:
    share = (
        tx.groupby(["order_year", "payment_method"])["transaction_id"]
        .count()
        .unstack(fill_value=0)
    )
    share = share.div(share.sum(axis=1), axis=0) * 100
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.stackplot(share.index, share.T.values, labels=share.columns, colors=PALETTE[: share.shape[1]], alpha=0.9)
    ax.set_title("Payment Method Market Share, 2015–2025")
    ax.set_ylabel("Share of orders (%)")
    ax.set_xlabel("Year")
    ax.legend(loc="upper left", ncol=2, fontsize=8)
    ax.set_ylim(0, 100)
    _save(fig, "04_payment_evolution.png")
    metrics["q4"] = {
        "share_2015": share.loc[share.index.min()].to_dict(),
        "share_2025": share.loc[share.index.max()].to_dict(),
        "upi_2015": float(share.loc[share.index.min()].get("UPI", 0)),
        "upi_2025": float(share.loc[share.index.max()].get("UPI", 0)),
        "cod_2015": float(share.loc[share.index.min()].get("COD", 0)),
        "cod_2025": float(share.loc[share.index.max()].get("COD", 0)),
    }


def q5_category_performance(tx: pd.DataFrame, metrics: dict) -> None:
    cat = tx.groupby("subcategory", as_index=False).agg(
        revenue=("final_amount_inr", "sum"),
        units=("quantity", "sum"),
        orders=("transaction_id", "count"),
    )
    cat["share"] = cat["revenue"] / cat["revenue"].sum()
    yoy = tx.groupby(["order_year", "subcategory"])["final_amount_inr"].sum().unstack()
    growth = ((yoy.iloc[-1] / yoy.iloc[0]) ** (1 / (len(yoy) - 1)) - 1) * 100

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    axes[0].barh(cat.sort_values("revenue")["subcategory"], _inr_cr(cat.sort_values("revenue")["revenue"]), color=AMAZON_ORANGE)
    axes[0].set_title("Revenue by Subcategory")
    axes[0].set_xlabel("₹ Cr")
    axes[1].pie(cat["revenue"], labels=cat["subcategory"], autopct="%1.1f%%", colors=PALETTE[: len(cat)])
    axes[1].set_title("Market Share")
    # Treemap-style via squarish bars of share
    axes[2].bar(growth.index, growth.values, color=AMAZON_NAVY)
    axes[2].set_title("CAGR 2015–2025 (%)")
    axes[2].tick_params(axis="x", rotation=35)
    fig.tight_layout()
    _save(fig, "05_category_performance.png")

    fig, ax = plt.subplots(figsize=(10, 6))
    sizes = cat["revenue"].values
    labels = [f"{n}\n{s:.1%}" for n, s in zip(cat["subcategory"], cat["share"])]
    _mpl_treemap(ax, sizes, labels, PALETTE[: len(cat)])
    ax.set_title("Subcategory Revenue Treemap")
    ax.axis("off")
    _save(fig, "05b_category_treemap.png")
    metrics["q5"] = {
        "revenue_by_subcategory": cat.set_index("subcategory")["revenue"].to_dict(),
        "share": cat.set_index("subcategory")["share"].to_dict(),
        "cagr_pct": growth.to_dict(),
    }


def _mpl_treemap(ax, sizes, labels, colors) -> None:
    sizes = np.asarray(sizes, dtype=float)
    sizes = sizes / sizes.sum()
    x, y, remaining = 0.0, 0.0, 1.0
    vertical = True
    for size, label, color in zip(sizes, labels, colors):
        if vertical:
            w, h = size / remaining if remaining else size, remaining
            ax.add_patch(plt.Rectangle((x, y), w, h, facecolor=color, edgecolor="white", lw=2))
            ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=9, color="white", weight="bold")
            x += w
            remaining -= size
            vertical = False if remaining > 0 and size < remaining else vertical
        else:
            w, h = remaining, size / remaining if remaining else size
            ax.add_patch(plt.Rectangle((x, y), w, h, facecolor=color, edgecolor="white", lw=2))
            ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=9, color="white", weight="bold")
            y += h
            remaining -= size
            vertical = True
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)


def q6_prime_impact(tx: pd.DataFrame, metrics: dict) -> None:
    grp = tx.groupby("is_prime_member").agg(
        orders=("transaction_id", "count"),
        customers=("customer_id", "nunique"),
        revenue=("final_amount_inr", "sum"),
        aov=("final_amount_inr", "mean"),
        freq=("transaction_id", "count"),
    )
    per_cust = tx.groupby(["customer_id", "is_prime_member"], as_index=False).agg(
        orders=("transaction_id", "count"), aov=("final_amount_inr", "mean"), spend=("final_amount_inr", "sum")
    )
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    aov = per_cust.groupby("is_prime_member")["aov"].mean()
    axes[0].bar(["Non-Prime", "Prime"], aov.reindex([False, True]).values, color=[AMAZON_NAVY, AMAZON_ORANGE])
    axes[0].set_title("Average Order Value")
    freq = per_cust.groupby("is_prime_member")["orders"].mean()
    axes[1].bar(["Non-Prime", "Prime"], freq.reindex([False, True]).values, color=[AMAZON_NAVY, AMAZON_ORANGE])
    axes[1].set_title("Orders per Customer")
    mix = pd.crosstab(tx["is_prime_member"], tx["subcategory"], normalize="index") * 100
    mix.index = mix.index.map({False: "Non-Prime", True: "Prime"})
    mix.T.plot(kind="bar", ax=axes[2], color=[AMAZON_NAVY, AMAZON_ORANGE])
    axes[2].set_title("Category Mix (%)")
    axes[2].tick_params(axis="x", rotation=35)
    fig.tight_layout()
    _save(fig, "06_prime_impact.png")
    metrics["q6"] = {
        "aov_prime": float(aov.get(True, np.nan)),
        "aov_nonprime": float(aov.get(False, np.nan)),
        "orders_per_cust_prime": float(freq.get(True, np.nan)),
        "orders_per_cust_nonprime": float(freq.get(False, np.nan)),
        "revenue_share_prime": float(tx.loc[tx["is_prime_member"], "final_amount_inr"].sum() / tx["final_amount_inr"].sum()),
    }


def q7_geography(tx: pd.DataFrame, metrics: dict) -> None:
    city = tx.groupby(["customer_city", "customer_tier", "customer_state"], as_index=False).agg(
        revenue=("final_amount_inr", "sum"), orders=("transaction_id", "count")
    )
    city["lat"] = city["customer_city"].map(lambda c: CITY_COORDS.get(c, (np.nan, np.nan))[0])
    city["lon"] = city["customer_city"].map(lambda c: CITY_COORDS.get(c, (np.nan, np.nan))[1])
    state = tx.groupby("customer_state")["final_amount_inr"].sum().sort_values()
    tier = tx.groupby("customer_tier")["final_amount_inr"].sum().reindex(["Metro", "Tier1", "Tier2", "Rural"])
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    axes[0].scatter(city["lon"], city["lat"], s=city["revenue"] / city["revenue"].max() * 800, c=city["revenue"], cmap="YlOrRd", alpha=0.75)
    for _, r in city.nlargest(8, "revenue").iterrows():
        axes[0].annotate(r["customer_city"], (r["lon"], r["lat"]), fontsize=7)
    axes[0].set_title("City Revenue Density")
    axes[0].set_xlabel("Longitude")
    axes[0].set_ylabel("Latitude")
    axes[1].barh(state.index, _inr_cr(state.values), color=AMAZON_ORANGE)
    axes[1].set_title("Revenue by State")
    axes[2].bar(tier.index.astype(str), _inr_cr(tier.values), color=PALETTE[:4])
    axes[2].set_title("Revenue by City Tier")
    fig.tight_layout()
    _save(fig, "07_geography.png")
    metrics["q7"] = {
        "top_cities": city.nlargest(10, "revenue")[["customer_city", "revenue", "customer_tier"]].to_dict(orient="records"),
        "tier_revenue": {str(k): float(v) for k, v in tier.items()},
        "top_states": {str(k): float(v) for k, v in state.sort_values(ascending=False).head(8).items()},
    }


def q8_festival(tx: pd.DataFrame, metrics: dict) -> None:
    daily = tx.groupby(["order_date", "is_festival_sale", "festival_name"], as_index=False)["final_amount_inr"].sum()
    fest_rev = tx.groupby("festival_name")["final_amount_inr"].sum().dropna().sort_values(ascending=False)
    fig, axes = plt.subplots(2, 1, figsize=(14, 8))
    monthly = tx.groupby(tx["order_date"].dt.to_period("M")).agg(
        revenue=("final_amount_inr", "sum"),
        festival_share=("is_festival_sale", "mean"),
    )
    monthly.index = monthly.index.to_timestamp()
    axes[0].plot(monthly.index, _inr_cr(monthly["revenue"]), color=AMAZON_NAVY, lw=1)
    spike = monthly[monthly["festival_share"] > 0.4]
    axes[0].scatter(spike.index, _inr_cr(spike["revenue"]), color=AMAZON_ORANGE, s=18, label="Festival-heavy months")
    axes[0].set_title("Revenue Time Series with Festival Spikes")
    axes[0].legend()
    axes[1].barh(fest_rev.index[::-1], _inr_cr(fest_rev.values[::-1]), color=AMAZON_ORANGE)
    axes[1].set_title("Revenue During Each Festival")
    axes[1].set_xlabel("₹ Cr")
    fig.tight_layout()
    _save(fig, "08_festival_impact.png")

    # before/during/after around Diwali using festival flag windows
    diwali = tx[tx["festival_name"] == "Diwali Sale"].copy()
    if len(diwali):
        windows = []
        for year, g in diwali.groupby(diwali["order_date"].dt.year):
            start, end = g["order_date"].min(), g["order_date"].max()
            before = tx[(tx["order_date"] >= start - pd.Timedelta(days=14)) & (tx["order_date"] < start)]
            after = tx[(tx["order_date"] > end) & (tx["order_date"] <= end + pd.Timedelta(days=14))]
            windows.append(
                {
                    "year": int(year),
                    "before_daily": float(before["final_amount_inr"].sum() / max((start - (start - pd.Timedelta(days=14))).days, 1)),
                    "during_daily": float(g["final_amount_inr"].sum() / max((end - start).days + 1, 1)),
                    "after_daily": float(after["final_amount_inr"].sum() / max(14, 1)),
                }
            )
        metrics["q8"] = {
            "festival_revenue": fest_rev.to_dict(),
            "festival_order_share": float(tx["is_festival_sale"].mean()),
            "diwali_before_during_after": windows,
        }
    else:
        metrics["q8"] = {"festival_revenue": fest_rev.to_dict(), "festival_order_share": float(tx["is_festival_sale"].mean())}


def q9_age(tx: pd.DataFrame, metrics: dict) -> None:
    age_order = ["18-25", "26-35", "36-45", "46-55", "55+", "Unknown"]
    spend = tx.groupby("customer_age_group")["final_amount_inr"].agg(["sum", "mean", "count"])
    mix = pd.crosstab(tx["customer_age_group"], tx["subcategory"], normalize="index") * 100
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    spend = spend.reindex(age_order)
    axes[0].bar(spend.index, _inr_cr(spend["sum"]), color=AMAZON_ORANGE)
    axes[0].set_title("Revenue by Age Group")
    axes[0].tick_params(axis="x", rotation=30)
    axes[1].bar(spend.index, spend["mean"], color=AMAZON_NAVY)
    axes[1].set_title("AOV by Age Group")
    axes[1].tick_params(axis="x", rotation=30)
    sns.heatmap(mix.reindex(age_order), cmap="YlOrBr", ax=axes[2])
    axes[2].set_title("Category Preference (%)")
    fig.tight_layout()
    _save(fig, "09_age_demographics.png")
    freq = tx.groupby(["customer_id", "customer_age_group"]).size().groupby("customer_age_group").mean()
    metrics["q9"] = {
        "revenue": spend["sum"].to_dict(),
        "aov": spend["mean"].to_dict(),
        "orders_per_customer": freq.to_dict(),
    }


def q10_price_demand(tx: pd.DataFrame, metrics: dict) -> None:
    prod = tx.groupby(["product_id", "subcategory"], as_index=False).agg(
        price=("discounted_price_inr", "median"),
        units=("quantity", "sum"),
        revenue=("final_amount_inr", "sum"),
        discount=("discount_percent", "mean"),
    )
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    sample = prod.sample(min(len(prod), 2000), random_state=42)
    for i, sub in enumerate(sample["subcategory"].unique()):
        part = sample[sample["subcategory"] == sub]
        axes[0].scatter(part["price"], part["units"], s=18, alpha=0.6, label=sub, color=PALETTE[i % len(PALETTE)])
    axes[0].set_xscale("log")
    axes[0].set_yscale("log")
    axes[0].set_xlabel("Median discounted price")
    axes[0].set_ylabel("Units sold")
    axes[0].set_title("Price vs Demand")
    axes[0].legend(fontsize=7)
    corr = prod[["price", "units", "revenue", "discount"]].corr()
    sns.heatmap(corr, annot=True, cmap="coolwarm", center=0, ax=axes[1], fmt=".2f")
    axes[1].set_title("Price-Demand Correlation")
    fig.tight_layout()
    _save(fig, "10_price_demand.png")
    metrics["q10"] = {"correlation": corr.to_dict()}


def q11_delivery(tx: pd.DataFrame, metrics: dict) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    sns.histplot(tx["delivery_days"], bins=np.arange(0.5, 8.5, 1), ax=axes[0], color=AMAZON_ORANGE)
    axes[0].set_title("Delivery Days Distribution")
    city = tx.groupby("customer_tier").agg(avg_days=("delivery_days", "mean"), rating=("customer_rating", "mean"))
    axes[1].bar(city.index.astype(str), city["avg_days"], color=AMAZON_NAVY)
    axes[1].set_title("Avg Delivery Days by Tier")
    rating_by_days = tx.groupby("delivery_days")["customer_rating"].mean()
    axes[2].plot(rating_by_days.index, rating_by_days.values, marker="o", color=AMAZON_ORANGE)
    axes[2].set_title("Customer Rating vs Delivery Speed")
    axes[2].set_xlabel("Delivery days")
    fig.tight_layout()
    _save(fig, "11_delivery_performance.png")
    on_time = (tx["delivery_days"] <= tx["delivery_type"].map({"Same Day": 1, "Express": 2, "Standard": 7})).mean()
    metrics["q11"] = {
        "avg_delivery_days": float(tx["delivery_days"].mean()),
        "median_delivery_days": float(tx["delivery_days"].median()),
        "on_time_vs_sla": float(on_time),
        "rating_by_days": rating_by_days.to_dict(),
        "avg_days_by_tier": city["avg_days"].to_dict(),
    }


def q12_returns(tx: pd.DataFrame, metrics: dict) -> None:
    tx = tx.assign(is_return=tx["return_status"].eq("Returned"), is_cancel=tx["return_status"].eq("Cancelled"))
    by_cat = tx.groupby("subcategory")["is_return"].mean().sort_values()
    by_status = tx["return_status"].value_counts(normalize=True)
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    axes[0].bar(by_status.index, by_status.values * 100, color=[AMAZON_NAVY, AMAZON_ORANGE, "#B12704"])
    axes[0].set_title("Order Status Mix (%)")
    axes[1].barh(by_cat.index, by_cat.values * 100, color=AMAZON_ORANGE)
    axes[1].set_title("Return Rate by Subcategory")
    bucket = pd.qcut(tx["discounted_price_inr"], 5, labels=["Q1 cheap", "Q2", "Q3", "Q4", "Q5 expensive"])
    rate = tx.groupby(bucket).agg(ret=("is_return", "mean"), rating=("customer_rating", "mean"), prod=("product_rating", "mean"))
    axes[2].plot(rate.index.astype(str), rate["ret"] * 100, marker="o", color="#B12704", label="Return %")
    ax2 = axes[2].twinx()
    ax2.plot(rate.index.astype(str), rate["rating"], marker="s", color=AMAZON_NAVY, label="Cust. rating")
    axes[2].set_title("Returns & Ratings by Price Quintile")
    fig.tight_layout()
    _save(fig, "12_returns.png")
    metrics["q12"] = {
        "return_rate": float(tx["is_return"].mean()),
        "cancel_rate": float(tx["is_cancel"].mean()),
        "return_by_subcategory": by_cat.to_dict(),
        "return_by_price_quintile": rate["ret"].to_dict(),
    }


def q13_brands(tx: pd.DataFrame, metrics: dict) -> None:
    yearly = tx.groupby(["order_year", "brand"])["final_amount_inr"].sum().unstack(fill_value=0)
    share = yearly.div(yearly.sum(axis=1), axis=0) * 100
    top = tx.groupby("brand")["final_amount_inr"].sum().nlargest(8).index
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    for i, brand in enumerate(top):
        axes[0].plot(share.index, share[brand], marker="o", label=brand, color=PALETTE[i % len(PALETTE)])
    axes[0].set_title("Brand Market Share Evolution")
    axes[0].legend(fontsize=8)
    axes[0].set_ylabel("% of revenue")
    totals = tx.groupby("brand")["final_amount_inr"].sum().sort_values(ascending=False).head(12)
    axes[1].barh(totals.index[::-1], _inr_cr(totals.values[::-1]), color=AMAZON_ORANGE)
    axes[1].set_title("Top Brands by Revenue")
    fig.tight_layout()
    _save(fig, "13_brand_performance.png")
    metrics["q13"] = {
        "top_brands": totals.to_dict(),
        "share_2015": share.loc[share.index.min(), top].to_dict(),
        "share_2025": share.loc[share.index.max(), top].to_dict(),
    }


def q14_clv_cohort(tx: pd.DataFrame, customers: pd.DataFrame, metrics: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    sns.histplot(np.log10(customers["clv"].clip(lower=1)), bins=40, ax=axes[0], color=AMAZON_ORANGE)
    axes[0].set_title("CLV Distribution (log10 INR)")
    axes[0].set_xlabel("log10 CLV")
    # cohort retention by acquisition year vs order year
    first = tx.groupby("customer_id")["order_date"].min().dt.year.rename("acq_year")
    merged = tx[["customer_id", "order_year"]].merge(first, on="customer_id")
    merged["period"] = merged["order_year"] - merged["acq_year"]
    cohort = merged.groupby(["acq_year", "period"])["customer_id"].nunique().unstack()
    retention = cohort.div(cohort[0], axis=0)
    sns.heatmap(retention, cmap="YlOrBr", ax=axes[1], vmin=0, vmax=1)
    axes[1].set_title("Annual Cohort Retention")
    fig.tight_layout()
    _save(fig, "14_clv_cohort.png")
    metrics["q14"] = {
        "median_clv": float(customers["clv"].median()),
        "mean_clv": float(customers["clv"].mean()),
        "retention_year1": {int(k): float(v) for k, v in retention[1].dropna().items()} if 1 in retention.columns else {},
        "clv_by_segment": customers.groupby("rfm_segment")["clv"].median().to_dict(),
        "clv_by_acq_year": customers.groupby("acquisition_year")["clv"].median().to_dict(),
    }


def q15_discounts(tx: pd.DataFrame, metrics: dict) -> None:
    tx = tx.copy()
    tx["disc_bin"] = pd.cut(tx["discount_percent"], bins=[-0.01, 0, 10, 20, 30, 50, 80], labels=["0%", "0-10", "10-20", "20-30", "30-50", "50+"])
    agg = tx.groupby("disc_bin").agg(orders=("transaction_id", "count"), revenue=("final_amount_inr", "sum"), units=("quantity", "sum"), aov=("final_amount_inr", "mean"))
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].bar(agg.index.astype(str), agg["units"], color=AMAZON_ORANGE)
    axes[0].set_title("Units Sold by Discount Band")
    corr = tx[["discount_percent", "quantity", "final_amount_inr", "original_price_inr"]].corr()
    sns.heatmap(corr, annot=True, cmap="coolwarm", center=0, ax=axes[1], fmt=".2f")
    axes[1].set_title("Discount Correlations")
    fig.tight_layout()
    _save(fig, "15_discount_effectiveness.png")
    yearly = tx.groupby(["order_year", "disc_bin"])["final_amount_inr"].sum().unstack(fill_value=0)
    metrics["q15"] = {
        "orders_by_band": agg["orders"].to_dict(),
        "revenue_by_band": agg["revenue"].to_dict(),
        "correlation": corr.to_dict(),
        "avg_discount": float(tx["discount_percent"].mean()),
    }


def q16_ratings_sales(tx: pd.DataFrame, metrics: dict) -> None:
    prod = tx.groupby(["product_id", "subcategory"], as_index=False).agg(
        product_rating=("product_rating", "mean"),
        customer_rating=("customer_rating", "mean"),
        revenue=("final_amount_inr", "sum"),
        units=("quantity", "sum"),
        price=("discounted_price_inr", "median"),
    )
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    sns.histplot(tx["product_rating"], bins=20, ax=axes[0], color=AMAZON_NAVY)
    axes[0].set_title("Product Rating Distribution")
    axes[1].scatter(prod["product_rating"], prod["units"], s=12, alpha=0.4, color=AMAZON_ORANGE)
    axes[1].set_title("Rating vs Units")
    prod["price_band"] = pd.qcut(prod["price"], 4, labels=["Low", "Mid-Low", "Mid-High", "High"])
    sns.boxplot(data=prod, x="price_band", y="product_rating", ax=axes[2], color=AMAZON_LIGHT if False else AMAZON_ORANGE)
    axes[2].set_title("Ratings by Price Band")
    fig.tight_layout()
    _save(fig, "16_ratings_sales.png")
    metrics["q16"] = {
        "rating_vs_units_corr": float(prod["product_rating"].corr(prod["units"])),
        "rating_vs_revenue_corr": float(prod["product_rating"].corr(prod["revenue"])),
        "mean_product_rating": float(tx["product_rating"].mean()),
        "mean_customer_rating": float(tx["customer_rating"].mean()),
    }


def q17_customer_journey(tx: pd.DataFrame, customers: pd.DataFrame, metrics: dict) -> None:
    orders = tx.groupby("customer_id")["transaction_id"].nunique()
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    vc = orders.clip(upper=10).value_counts().sort_index()
    axes[0].bar(vc.index.astype(str), vc.values, color=AMAZON_ORANGE)
    axes[0].set_title("Purchase Frequency (capped at 10+)")
    axes[0].set_xlabel("Orders per customer")
    seq = tx.sort_values(["customer_id", "order_date"]).copy()
    seq["prev"] = seq.groupby("customer_id")["subcategory"].shift()
    moved = seq.dropna(subset=["prev"])
    trans = moved.groupby(["prev", "subcategory"]).size()
    transitions = trans.to_dict()
    cats = sorted(tx["subcategory"].unique())
    mat = pd.DataFrame(0, index=cats, columns=cats, dtype=float)
    for (a, b), n in transitions.items():
        mat.loc[a, b] = n
    mat = mat.div(mat.sum(axis=1).replace(0, np.nan), axis=0)
    sns.heatmap(mat, cmap="YlOrBr", ax=axes[1], annot=False)
    axes[1].set_title("Subcategory Transition Matrix")
    fig.tight_layout()
    _save(fig, "17_customer_journey.png")
    loyal = (orders >= 5).mean()
    one_time = (orders == 1).mean()
    metrics["q17"] = {
        "one_time_customer_share": float(one_time),
        "loyal_5plus_share": float(loyal),
        "mean_orders_per_customer": float(orders.mean()),
        "top_transitions": sorted(
            ((f"{a}→{b}", n) for (a, b), n in transitions.items()), key=lambda x: -x[1]
        )[:8],
    }


def q18_product_lifecycle(tx: pd.DataFrame, products: pd.DataFrame, metrics: dict) -> None:
    yearly_prod = tx.groupby(["product_id", "order_year"])["quantity"].sum().unstack(fill_value=0)
    # launch success: first-year units vs later
    first_year = products[["product_id", "launch_year"]].merge(
        tx.groupby(["product_id", "order_year"])["final_amount_inr"].sum().reset_index(),
        on="product_id",
        how="left",
    )
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    launch = tx.merge(products[["product_id", "launch_year"]], on="product_id", how="left")
    launch["age"] = launch["order_year"] - launch["launch_year"]
    age_rev = launch[launch["age"] >= 0].groupby("age")["final_amount_inr"].mean()
    axes[0].plot(age_rev.index, _inr_cr(age_rev.values), marker="o", color=AMAZON_ORANGE)
    axes[0].set_title("Avg Transaction Revenue by Product Age (years since launch)")
    axes[0].set_xlabel("Years since launch")
    sub_year = tx.groupby(["order_year", "subcategory"])["final_amount_inr"].sum().unstack()
    sub_year.div(sub_year.sum(axis=1), axis=0).plot(ax=axes[1], color=PALETTE[: sub_year.shape[1]])
    axes[1].set_title("Subcategory Mix Over the Decade")
    axes[1].set_ylabel("Revenue share")
    fig.tight_layout()
    _save(fig, "18_product_lifecycle.png")
    metrics["q18"] = {
        "revenue_by_product_age": age_rev.to_dict(),
        "subcategory_share_2015": sub_year.div(sub_year.sum(axis=1), axis=0).iloc[0].to_dict(),
        "subcategory_share_2025": sub_year.div(sub_year.sum(axis=1), axis=0).iloc[-1].to_dict(),
    }


def q19_competitive_pricing(tx: pd.DataFrame, metrics: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    top_brands = tx.groupby("brand")["final_amount_inr"].sum().nlargest(8).index
    part = tx[tx["brand"].isin(top_brands)]
    sns.boxplot(data=part, x="brand", y="discounted_price_inr", ax=axes[0], showfliers=False, color=AMAZON_ORANGE)
    axes[0].tick_params(axis="x", rotation=35)
    axes[0].set_title("Price Positioning by Brand")
    pos = part.groupby("brand").agg(median_price=("discounted_price_inr", "median"), units=("quantity", "sum"), rating=("product_rating", "mean"))
    axes[1].scatter(pos["median_price"], pos["units"], s=pos["rating"] * 80, color=AMAZON_NAVY, alpha=0.8)
    for brand, r in pos.iterrows():
        axes[1].annotate(brand, (r["median_price"], r["units"]), fontsize=8)
    axes[1].set_xlabel("Median price")
    axes[1].set_ylabel("Units")
    axes[1].set_title("Competitive Matrix (size ≈ rating)")
    fig.tight_layout()
    _save(fig, "19_competitive_pricing.png")
    metrics["q19"] = pos.to_dict()


def q20_business_health(tx: pd.DataFrame, customers: pd.DataFrame, metrics: dict) -> None:
    yearly = tx.groupby("order_year").agg(
        revenue=("final_amount_inr", "sum"),
        orders=("transaction_id", "count"),
        customers=("customer_id", "nunique"),
        aov=("final_amount_inr", "mean"),
        prime_share=("is_prime_member", "mean"),
        return_rate=("return_status", lambda s: (s == "Returned").mean()),
        avg_delivery=("delivery_days", "mean"),
    )
    new_cust = customers.groupby("acquisition_year").size()
    yearly["new_customers"] = new_cust
    yearly["yoy"] = yearly["revenue"].pct_change()
    fig = plt.figure(figsize=(16, 9))
    gs = GridSpec(2, 3, figure=fig)
    ax1 = fig.add_subplot(gs[0, :2])
    ax1.plot(yearly.index, _inr_cr(yearly["revenue"]), marker="o", color=AMAZON_ORANGE, label="Revenue")
    ax1.set_title("Business Health — Revenue")
    ax1.legend()
    ax2 = fig.add_subplot(gs[0, 2])
    ax2.bar(yearly.index.astype(int).astype(str), yearly["yoy"] * 100, color=AMAZON_NAVY)
    ax2.set_title("YoY Growth %")
    ax2.tick_params(axis="x", rotation=45)
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.plot(yearly.index, yearly["customers"], marker="o", color=PALETTE[2], label="Active")
    ax3.plot(yearly.index, yearly["new_customers"], marker="s", color=PALETTE[3], label="New")
    ax3.set_title("Customer Acquisition")
    ax3.legend(fontsize=8)
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.plot(yearly.index, yearly["return_rate"] * 100, color="#B12704", marker="o")
    ax4.set_title("Return Rate %")
    ax5 = fig.add_subplot(gs[1, 2])
    ax5.plot(yearly.index, yearly["avg_delivery"], color=PALETTE[6], marker="o", label="Delivery days")
    ax5.plot(yearly.index, yearly["prime_share"] * 10, color=AMAZON_ORANGE, marker="s", label="Prime share x10")
    ax5.set_title("Ops Efficiency vs Prime Mix")
    ax5.legend(fontsize=8)
    fig.suptitle("Executive Business Health Dashboard", fontsize=16, color=AMAZON_NAVY, weight="bold")
    fig.tight_layout()
    _save(fig, "20_business_health.png")
    X = yearly.index.values.reshape(-1, 1)
    model = LinearRegression().fit(X, yearly["revenue"].values)
    metrics["q20"] = {
        "yearly": yearly.reset_index().to_dict(orient="records"),
        "linear_slope_inr_per_year": float(model.coef_[0]),
        "active_customers_2025": int(yearly.loc[yearly.index.max(), "customers"]),
        "return_rate_latest": float(yearly.loc[yearly.index.max(), "return_rate"]),
    }


def run_eda(tx: pd.DataFrame | None = None, customers=None, products=None) -> dict:
    _setup_style()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if tx is None:
        tx = pd.read_parquet(CLEANED_DIR / "transactions_cleaned.parquet")
    if customers is None:
        customers = pd.read_parquet(CLEANED_DIR / "customers.parquet")
    if products is None:
        products = pd.read_parquet(CLEANED_DIR / "products.parquet")
    metrics: dict = {}
    print("EDA Q1 revenue...")
    q1_revenue_trend(tx, metrics)
    print("EDA Q2 seasonality...")
    q2_seasonality(tx, metrics)
    print("EDA Q3 RFM...")
    q3_rfm(customers, metrics)
    print("EDA Q4 payments...")
    q4_payment_evolution(tx, metrics)
    print("EDA Q5 category...")
    q5_category_performance(tx, metrics)
    print("EDA Q6 prime...")
    q6_prime_impact(tx, metrics)
    print("EDA Q7 geo...")
    q7_geography(tx, metrics)
    print("EDA Q8 festival...")
    q8_festival(tx, metrics)
    print("EDA Q9 age...")
    q9_age(tx, metrics)
    print("EDA Q10 price-demand...")
    q10_price_demand(tx, metrics)
    print("EDA Q11 delivery...")
    q11_delivery(tx, metrics)
    print("EDA Q12 returns...")
    q12_returns(tx, metrics)
    print("EDA Q13 brands...")
    q13_brands(tx, metrics)
    print("EDA Q14 CLV...")
    q14_clv_cohort(tx, customers, metrics)
    print("EDA Q15 discounts...")
    q15_discounts(tx, metrics)
    print("EDA Q16 ratings...")
    q16_ratings_sales(tx, metrics)
    print("EDA Q17 journey...")
    q17_customer_journey(tx, customers, metrics)
    print("EDA Q18 lifecycle...")
    q18_product_lifecycle(tx, products, metrics)
    print("EDA Q19 pricing...")
    q19_competitive_pricing(tx, metrics)
    print("EDA Q20 health...")
    q20_business_health(tx, customers, metrics)
    (REPORTS_DIR / "eda_metrics.json").write_text(json.dumps(metrics, indent=2, default=str), encoding="utf-8")
    print("EDA complete →", FIGURES_DIR)
    return metrics


if __name__ == "__main__":
    run_eda()
