"""Typed loading with a schema contract: fail loudly rather than analyse bad input."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

MQL_COLUMNS = ["mql_id", "first_contact_date", "landing_page_id", "origin"]
DEAL_COLUMNS = [
    "mql_id", "seller_id", "sdr_id", "sr_id", "won_date", "business_segment",
    "lead_type", "lead_behaviour_profile", "has_company", "has_gtin",
    "average_stock", "business_type", "declared_product_catalog_size",
    "declared_monthly_revenue",
]
ORDER_COLUMNS = ["order_id", "order_status", "order_purchase_timestamp"]
ITEM_COLUMNS = ["order_id", "seller_id", "price"]


class ContractError(ValueError):
    """Raised when an input file breaks the schema contract."""


@dataclass
class RawData:
    mql: pd.DataFrame
    deals: pd.DataFrame
    orders: pd.DataFrame
    items: pd.DataFrame


def _require(df: pd.DataFrame, cols: list[str], name: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ContractError(f"{name}: missing columns {missing}")


def _require_unique(df: pd.DataFrame, col: str, name: str) -> None:
    dups = int(df[col].duplicated().sum())
    if dups:
        raise ContractError(f"{name}: {dups} duplicate values in {col}")


def _parse_dates(df: pd.DataFrame, col: str, name: str) -> None:
    parsed = pd.to_datetime(df[col], errors="coerce")
    bad = int(parsed.isna().sum() - df[col].isna().sum())
    if bad:
        raise ContractError(f"{name}: {bad} unparseable dates in {col}")
    df[col] = parsed


def validate(raw: RawData) -> RawData:
    _require(raw.mql, MQL_COLUMNS, "mql")
    _require(raw.deals, DEAL_COLUMNS, "deals")
    _require(raw.orders, ORDER_COLUMNS, "orders")
    _require(raw.items, ITEM_COLUMNS, "items")
    _require_unique(raw.mql, "mql_id", "mql")
    _require_unique(raw.deals, "mql_id", "deals")
    if raw.mql["first_contact_date"].isna().any():
        raise ContractError("mql: first_contact_date has blanks")
    if raw.deals["won_date"].isna().any():
        raise ContractError("deals: won_date has blanks")
    orphans = int((~raw.deals["mql_id"].isin(raw.mql["mql_id"])).sum())
    if orphans:
        raise ContractError(f"deals: {orphans} deals have no matching lead")
    _parse_dates(raw.mql, "first_contact_date", "mql")
    _parse_dates(raw.deals, "won_date", "deals")
    _parse_dates(raw.orders, "order_purchase_timestamp", "orders")
    raw.deals["declared_monthly_revenue"] = pd.to_numeric(
        raw.deals["declared_monthly_revenue"], errors="raise"
    )
    raw.items["price"] = pd.to_numeric(raw.items["price"], errors="raise")
    if (raw.items["price"] < 0).any():
        raise ContractError("items: negative prices")
    return raw


def load(raw_dir: Path) -> RawData:
    s = {"dtype": str, "keep_default_na": True}
    raw = RawData(
        mql=pd.read_csv(raw_dir / "olist_marketing_qualified_leads_dataset.csv", **s),
        deals=pd.read_csv(raw_dir / "olist_closed_deals_dataset.csv", **s),
        orders=pd.read_csv(raw_dir / "olist_orders_dataset.csv", usecols=ORDER_COLUMNS, **s),
        items=pd.read_csv(raw_dir / "olist_order_items_dataset.csv", usecols=ITEM_COLUMNS, **s),
    )
    return validate(raw)
