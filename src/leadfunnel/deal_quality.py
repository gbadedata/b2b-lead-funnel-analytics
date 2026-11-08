"""What happens after a deal is won: do the new sellers actually sell?

A channel that converts well but brings sellers who never trade is worth less
than its conversion rate suggests. This module links won deals to the public
order data and measures activity in the 90 days after the deal.
"""

from __future__ import annotations

import pandas as pd

from .config import SETTINGS, Settings
from .funnel import wilson

EXCLUDED_STATUSES = {"canceled", "unavailable"}


def seller_activity(
    won: pd.DataFrame, orders: pd.DataFrame, items: pd.DataFrame, s: Settings = SETTINGS
) -> pd.DataFrame:
    """Orders and GMV per won deal in the window (won_date, won_date + window]."""
    eligible = won[won["won_date"] < s.ts("deal_quality_won_end")].copy()
    ok = orders[~orders["order_status"].isin(EXCLUDED_STATUSES)]
    lines = items.merge(ok[["order_id", "order_purchase_timestamp"]], on="order_id")
    lines = lines.merge(eligible[["seller_id", "won_date"]], on="seller_id")
    end = lines["won_date"] + pd.Timedelta(days=s.window_days)
    in_window = (lines["order_purchase_timestamp"] > lines["won_date"]) & (
        lines["order_purchase_timestamp"] <= end
    )
    lines = lines[in_window]
    per_seller = lines.groupby("seller_id").agg(
        orders_90d=("order_id", "nunique"), gmv_90d=("price", "sum")
    )
    out = eligible.merge(per_seller, left_on="seller_id", right_index=True, how="left")
    out[["orders_90d", "gmv_90d"]] = out[["orders_90d", "gmv_90d"]].fillna(0)
    out["active_90d"] = out["orders_90d"] > 0
    return out


def activity_by(df: pd.DataFrame, by: str, s: Settings = SETTINGS) -> pd.DataFrame:
    g = df.groupby(by).agg(
        deals=("mql_id", "size"),
        active=("active_90d", "sum"),
        gmv_90d=("gmv_90d", "sum"),
    )
    g["activation_rate"] = g["active"] / g["deals"]
    g["ci_low"], g["ci_high"] = wilson(g["active"].to_numpy(), g["deals"].to_numpy())
    med = df[df["active_90d"]].groupby(by)["gmv_90d"].median()
    g["median_gmv_if_active"] = med.reindex(g.index)
    g["gmv_per_deal"] = g["gmv_90d"] / g["deals"]
    g["share_of_gmv"] = g["gmv_90d"] / g["gmv_90d"].sum()
    g["rankable"] = g["deals"] >= 30
    return g.sort_values("deals", ascending=False)
