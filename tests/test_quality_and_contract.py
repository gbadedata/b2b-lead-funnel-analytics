import pandas as pd
import pytest

from leadfunnel import funnel, quality
from leadfunnel.load import ContractError, RawData, validate


def test_contract_rejects_missing_column(raw):
    bad = RawData(raw.mql.drop(columns=["origin"]), raw.deals, raw.orders, raw.items)
    with pytest.raises(ContractError, match="origin"):
        validate(bad)


def test_contract_rejects_duplicate_leads(raw):
    mql = pd.concat([raw.mql, raw.mql.head(1)])
    with pytest.raises(ContractError, match="duplicate"):
        validate(RawData(mql, raw.deals, raw.orders, raw.items))


def test_contract_rejects_orphan_deal(raw):
    deals = raw.deals.copy()
    deals.loc[deals.index[0], "mql_id"] = "f" * 32
    with pytest.raises(ContractError, match="no matching lead"):
        validate(RawData(raw.mql, deals, raw.orders, raw.items))


def test_contract_rejects_bad_dates(raw):
    mql = raw.mql.copy()
    mql["first_contact_date"] = mql["first_contact_date"].astype(str)
    mql.loc[0, "first_contact_date"] = "not a date"
    with pytest.raises(ContractError, match="unparseable"):
        validate(RawData(mql, raw.deals, raw.orders, raw.items))


def test_quality_log_covers_every_check(raw):
    leads = funnel.build_leads(raw.mql, raw.deals)
    log = quality.run_checks(raw, leads)
    assert list(log["code"]) == [f"DQ{i:02d}" for i in range(1, 12)]
    assert set(log["severity"]) <= {"high", "medium", "low", "pass"}
    assert log["finding"].str.len().gt(10).all()
    assert log["recommendation"].str.len().gt(3).all()


def test_quality_counts_unattributed_and_zero_revenue(raw):
    leads = funnel.build_leads(raw.mql, raw.deals)
    log = quality.run_checks(raw, leads).set_index("code")
    expected_unattributed = raw.mql["origin"].isna().sum() + (raw.mql["origin"] == "unknown").sum()
    assert log.loc["DQ02", "affected"] == expected_unattributed
    assert log.loc["DQ05", "affected"] == (raw.deals["declared_monthly_revenue"] == 0).sum()
    assert log.loc["DQ03", "affected"] == len(raw.mql) - len(raw.deals)
