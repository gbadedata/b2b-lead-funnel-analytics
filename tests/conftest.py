"""Synthetic inputs shaped like the Olist files, so tests run offline and fast."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from leadfunnel.load import RawData, validate

ORIGINS = ["organic_search", "paid_search", "social", "unknown", "email", None]
RATES = {"organic_search": 0.12, "paid_search": 0.12, "social": 0.05, "unknown": 0.2, "email": 0.04, None: 0.2}


def make_raw(n: int = 1500, seed: int = 1) -> RawData:
    rng = np.random.default_rng(seed)
    dates = pd.to_datetime("2017-10-01") + pd.to_timedelta(rng.integers(0, 243, n), unit="D")
    origin = rng.choice(np.array(ORIGINS, dtype=object), n, p=[0.3, 0.2, 0.2, 0.15, 0.1, 0.05])
    pages = rng.choice([f"page{i:03d}" + "x" * 24 for i in range(40)], n, p=np.r_[[0.3, 0.2], [0.5 / 38] * 38])
    mql = pd.DataFrame({
        "mql_id": [f"{i:032x}" for i in range(n)],
        "first_contact_date": dates.strftime("%Y-%m-%d"),
        "landing_page_id": pages,
        "origin": origin,
    })
    p_win = np.array([RATES[o] for o in origin]) * np.where(pages == pages[0], 1.5, 1.0)
    won = rng.random(n) < p_win
    days = rng.integers(0, 150, n)
    won_date = dates + pd.to_timedelta(days, unit="D")
    # Deal records only start in December 2017, as in the real data.
    won &= won_date >= pd.Timestamp("2017-12-05")
    idx = np.flatnonzero(won)
    deals = pd.DataFrame({
        "mql_id": mql.loc[idx, "mql_id"].to_numpy(),
        "seller_id": [f"s{i:031d}" for i in idx],
        "sdr_id": "sdr", "sr_id": "sr",
        "won_date": won_date[idx].strftime("%Y-%m-%d 10:00:00"),
        "business_segment": "pet", "lead_type": rng.choice(["online_medium", "industry"], len(idx)),
        "lead_behaviour_profile": rng.choice(["cat", "wolf", None, "cat, wolf"], len(idx)),
        "has_company": None, "has_gtin": None, "average_stock": None, "business_type": "reseller",
        "declared_product_catalog_size": None,
        "declared_monthly_revenue": rng.choice(["0", "100000"], len(idx), p=[0.9, 0.1]),
    })
    # Orders: about half the won sellers sell after their won date.
    sellers = deals.sample(frac=0.5, random_state=seed)
    o_rows, i_rows = [], []
    for k, (_, d) in enumerate(sellers.iterrows()):
        t = pd.Timestamp(d["won_date"]) + pd.Timedelta(days=int(rng.integers(1, 120)))
        oid = f"o{k:031d}"
        o_rows.append({"order_id": oid, "order_status": "delivered", "order_purchase_timestamp": str(t)})
        i_rows.append({"order_id": oid, "seller_id": d["seller_id"], "price": f"{rng.uniform(10, 200):.2f}"})
    orders = pd.DataFrame(o_rows)
    items = pd.DataFrame(i_rows)
    return validate(RawData(mql=mql, deals=deals, orders=orders, items=items))


@pytest.fixture
def raw() -> RawData:
    return make_raw()
