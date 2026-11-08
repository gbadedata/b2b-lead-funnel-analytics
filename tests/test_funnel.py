import numpy as np
import pandas as pd
import pytest

from leadfunnel import funnel
from leadfunnel.config import SETTINGS


def _one_lead(days_to_win: int | None, origin="paid_search", contact="2018-02-01"):
    mql = pd.DataFrame({"mql_id": ["a"], "first_contact_date": [pd.Timestamp(contact)],
                        "landing_page_id": ["p"], "origin": [origin]})
    cols = ["mql_id", "seller_id", "sdr_id", "sr_id", "won_date", "business_segment", "lead_type",
            "business_type", "declared_monthly_revenue"]
    if days_to_win is None:
        deals = pd.DataFrame(columns=cols)
        deals["won_date"] = pd.to_datetime(deals["won_date"])
    else:
        deals = pd.DataFrame([{"mql_id": "a", "seller_id": "s", "sdr_id": "x", "sr_id": "y",
                               "won_date": pd.Timestamp(contact) + pd.Timedelta(days=days_to_win, hours=15),
                               "business_segment": "pet", "lead_type": "industry", "business_type": "reseller",
                               "declared_monthly_revenue": 0.0}])
    return funnel.build_leads(mql, deals)


@pytest.mark.parametrize("days,expected", [(0, True), (90, True), (91, False), (None, False)])
def test_ninety_day_window_is_inclusive(days, expected):
    assert bool(_one_lead(days)["won_90d"].iloc[0]) is expected


def test_won_before_contact_is_flagged_and_clipped():
    lead = _one_lead(-2).iloc[0]
    assert lead["won_before_contact"]
    assert lead["days_to_close"] == 0
    assert lead["won_90d"]


def test_blank_origin_becomes_missing_and_unattributed():
    lead = _one_lead(None, origin=None).iloc[0]
    assert lead["origin"] == "missing"
    assert lead["unattributed"]


def test_cohort_excludes_leads_before_deal_tracking(raw):
    leads = funnel.build_leads(raw.mql, raw.deals)
    c = funnel.cohort(leads)
    assert c["first_contact_date"].min() >= SETTINGS.ts("cohort_start")
    assert c["first_contact_date"].max() <= SETTINGS.ts("cohort_end")
    assert len(c) < len(leads)


def test_wilson_interval_properties():
    lo, hi = funnel.wilson(np.array([0, 5, 10]), np.array([10, 10, 10]))
    assert lo[0] == 0 and hi[0] > 0          # zero successes still gets an upper bound
    assert hi[2] == pytest.approx(1.0) and lo[2] < 1
    assert lo[1] < 0.5 < hi[1]
    assert lo[1] == pytest.approx(1 - hi[1])  # symmetric at p = 0.5
    # Known value: 5/10 -> 0.2366 to 0.7634
    assert lo[1] == pytest.approx(0.2366, abs=1e-4)


def test_holm_matches_hand_calculation():
    adj = funnel.holm(np.array([0.01, 0.04, 0.03]))
    assert adj == pytest.approx([0.03, 0.06, 0.06])


def test_rate_table_shares_sum_to_one(raw):
    c = funnel.cohort(funnel.build_leads(raw.mql, raw.deals))
    t = funnel.rate_table(c, "origin")
    assert t["share_of_leads"].sum() == pytest.approx(1)
    assert t["share_of_wins"].sum() == pytest.approx(1)
    assert (t["ci_low"] <= t["rate"]).all() and (t["rate"] <= t["ci_high"]).all()


def test_shrinkage_pulls_small_pages_toward_prior():
    df = pd.DataFrame({
        "landing_page_id": ["tiny"] * 1 + ["big"] * 400 + [f"p{i}" for i in range(200) for _ in range(5)],
        "won_90d": [True] + [True] * 60 + [False] * 340 + list(np.random.default_rng(0).random(1000) < 0.1),
    })
    pages, prior = funnel.landing_page_table(df)
    tiny, big = pages.loc["tiny"], pages.loc["big"]
    assert tiny["raw_rate"] == 1.0
    assert tiny["shrunk_rate"] < 0.5                                   # one lucky lead is not 100%
    assert abs(big["shrunk_rate"] - big["raw_rate"]) < 0.01            # big pages barely move
    assert prior["prior_mean"] < tiny["shrunk_rate"] < tiny["raw_rate"]


def test_cumulative_conversion_ends_at_window_rate(raw):
    c = funnel.cohort(funnel.build_leads(raw.mql, raw.deals))
    curves = funnel.cumulative_conversion(c)
    rates = c.groupby("origin")["won_90d"].mean()
    for o in curves.columns:
        assert curves[o].iloc[-1] == pytest.approx(rates[o])
        assert curves[o].is_monotonic_increasing


def test_adjusted_odds_ratios_run_and_are_positive(raw):
    c = funnel.cohort(funnel.build_leads(raw.mql, raw.deals))
    od = funnel.adjusted_odds_ratios(c)
    assert "organic_search" not in set(od["origin"])  # reference level
    assert (od["odds_ratio"] > 0).all()
    assert (od["p_holm"] >= od["p_value"]).all()
