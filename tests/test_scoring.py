import numpy as np
import pandas as pd
import pytest

from leadfunnel import deal_quality, funnel, scoring
from leadfunnel.config import SETTINGS


@pytest.fixture
def cohort(raw):
    return funnel.cohort(funnel.build_leads(raw.mql, raw.deals))


def test_time_split_has_no_overlap(cohort):
    tr, te = scoring.time_split(cohort)
    assert tr["first_contact_date"].max() < te["first_contact_date"].min()
    assert len(tr) + len(te) == len(cohort)


def test_target_encoding_never_uses_own_outcome():
    train = pd.DataFrame({"page": ["solo", "a", "a", "a", "a", "a", "a"], "y": [1, 0, 0, 0, 1, 0, 0]})
    test = pd.DataFrame({"page": ["solo", "new"]})
    tr, te = scoring.target_encode(train, test, "page", "y", m=5, seed=0, folds=7)
    prior = train["y"].mean()
    # Leave-one-out style: the single-lead page cannot see its own win.
    assert tr[0] == pytest.approx(prior)
    # Unseen page in test falls back to the prior.
    assert te[1] == pytest.approx(prior)
    # Test rows use full-train statistics.
    assert te[0] == pytest.approx((1 + 5 * prior) / (1 + 5))


def test_gains_perfect_and_random():
    y = np.array([1, 1, 0, 0, 0, 0, 0, 0, 0, 0])
    perfect = scoring.gains(y, y.astype(float), fractions=(0.2, 0.5))
    assert perfect["top_20pct"] == 1.0
    reverse = scoring.gains(y, -y.astype(float), fractions=(0.2,))
    assert reverse["top_20pct"] == 0.0


def test_scoring_run_reports_honest_test_metrics(cohort):
    res = scoring.run(cohort)
    m = res["metrics"]
    assert res["test"]["leads"] == len(res["scored_test"])
    for k in ("channel_only", "logistic", "gradient_boosting"):
        assert 0 <= m[k]["roc_auc"] <= 1
        assert m[k]["top_10pct"] <= m[k]["top_20pct"] <= m[k]["top_50pct"]
    # Features must not include anything from the closed-deal record.
    assert all(k.startswith(("source=", "weekday=", "page_")) for k in res["logistic_coefficients"])
    assert set(res["scored_test"]["decile"]) == set(range(1, 11))


def test_deal_activity_window_and_status(raw):
    won = pd.DataFrame({"mql_id": ["m1", "m2", "m3"], "seller_id": ["s1", "s2", "s3"],
                        "won_date": pd.to_datetime(["2018-02-01", "2018-02-01", "2018-07-01"]),
                        "origin": ["email"] * 3})
    orders = pd.DataFrame({
        "order_id": ["o1", "o2", "o3", "o4"],
        "order_status": ["delivered", "canceled", "delivered", "delivered"],
        "order_purchase_timestamp": pd.to_datetime(["2018-03-01", "2018-03-01", "2018-06-01", "2018-07-02"]),
    })
    items = pd.DataFrame({"order_id": ["o1", "o2", "o3", "o4"], "seller_id": ["s1", "s2", "s1", "s3"],
                          "price": [10.0, 99.0, 50.0, 5.0]})
    act = deal_quality.seller_activity(won, orders, items).set_index("seller_id")
    assert act.loc["s1", "gmv_90d"] == 10.0          # o3 is 120 days later: outside the window
    assert not act.loc["s2", "active_90d"]           # cancelled order does not count
    assert "s3" not in act.index                     # won after the cut-off: no full window
    assert SETTINGS.window_days == 90


def test_group_origins_pools_unattributed_and_small_sources():
    train = pd.DataFrame({"origin": ["unknown"] * 3 + ["missing"] * 2 + ["email"] * 5 + ["display"]})
    test = pd.DataFrame({"origin": ["missing", "display", "brand_new"]})
    tr, te = scoring.group_origins(train, test, min_n=5)
    assert set(tr) == {"unattributed", "email", "other_small"}
    assert list(te) == ["unattributed", "other_small", "other_small"]
