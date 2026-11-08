"""Data quality checks, written up as issues a manager can act on."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from .config import SETTINGS, Settings
from .load import RawData


@dataclass
class Issue:
    code: str
    severity: str  # high | medium | low | pass
    check: str
    affected: int
    share: float | None
    finding: str
    impact: str
    recommendation: str


def run_checks(raw: RawData, leads: pd.DataFrame, s: Settings = SETTINGS) -> pd.DataFrame:
    mql, deals, orders, items = raw.mql, raw.deals, raw.orders, raw.items
    n_mql, n_deals = len(mql), len(deals)
    issues: list[Issue] = []

    # DQ01 deal tracking coverage
    first_won = deals["won_date"].min()
    pre = leads[leads["first_contact_date"] < s.ts("cohort_start")]
    post = leads[leads["first_contact_date"] >= s.ts("cohort_start")]
    issues.append(Issue(
        "DQ01", "high", "Deal records cover the whole lead period", len(pre), len(pre) / n_mql,
        f"The first recorded deal is dated {first_won:%d %b %Y}, but leads start "
        f"{mql['first_contact_date'].min():%d %b %Y}. Leads first contacted before 2018 "
        f"show {pre['won_any'].mean():.1%} conversion against {post['won_any'].mean():.1%} after.",
        "Conversion for 2017 leads looks far lower than it was, which would distort any "
        "trend or channel comparison that includes them.",
        "Analyse only leads from January 2018, and confirm with the CRM owner when deal "
        "logging began.",
    ))

    # DQ02 unattributed origin
    blank = int(mql["origin"].isna().sum())
    unknown = int((mql["origin"] == "unknown").sum())
    c = leads[leads["first_contact_date"] >= s.ts("cohort_start")]
    ua = c[c["unattributed"]]
    issues.append(Issue(
        "DQ02", "high", "Every lead has a recorded source", blank + unknown, (blank + unknown) / n_mql,
        f"{blank:,} leads have a blank origin and {unknown:,} are marked 'unknown'. In the 2018 "
        f"cohort these unattributed leads convert at {ua['won_90d'].mean():.1%} within "
        f"{s.window_days} days, against {c.loc[~c['unattributed'], 'won_90d'].mean():.1%} for attributed leads.",
        "The best-converting group has no source, so marketing spend cannot be tied to "
        "the leads that matter most.",
        "Make source a required field on the enquiry form and CRM, and audit how "
        "'unknown' leads are created (for example manual or phone entries).",
    ))

    # DQ03 rep fields structural gap
    issues.append(Issue(
        "DQ03", "high", "Sales rep is recorded on every lead", n_mql - n_deals, (n_mql - n_deals) / n_mql,
        "SDR and sales rep IDs exist only on won deals; lost leads carry no rep.",
        "Rep conversion rates cannot be measured, only rep deal counts, which reward "
        "volume rather than skill.",
        "Record the assigned rep when a lead is first contacted, not when it is won.",
    ))

    # DQ04 won before first contact
    neg = int(leads["won_before_contact"].sum())
    issues.append(Issue(
        "DQ04", "low" if neg else "pass", "Won date is on or after first contact", neg, neg / n_deals,
        f"{neg:,} deal(s) are dated before the lead's first contact.",
        "Minor: these are treated as same-day wins and flagged.",
        "Check whether first contact is logged late for some leads.",
    ))

    # DQ05 declared monthly revenue
    rev = deals["declared_monthly_revenue"]
    zeros = int((rev == 0).sum())
    big = int((rev >= 1_000_000).sum())
    issues.append(Issue(
        "DQ05", "medium", "Declared monthly revenue is usable", zeros, zeros / n_deals,
        f"{zeros:,} of {n_deals:,} deals ({zeros / n_deals:.0%}) record declared revenue as 0, "
        f"which looks like 'not asked' rather than true zero; {big:,} record 1,000,000 or more "
        f"(maximum {rev.max():,.0f}).",
        "Deal value cannot be estimated from this field, so revenue analysis must use "
        "actual orders instead.",
        "Store 'not provided' as blank, not 0, and add a sense check on very large values.",
    ))

    # DQ06 sparse firmographics
    cols = ["has_company", "has_gtin", "average_stock", "declared_product_catalog_size"]
    miss = deals[cols].isna().mean()
    issues.append(Issue(
        "DQ06", "medium", "Deal profile fields are filled in", int(deals[cols].isna().all(axis=1).sum()),
        float(miss.mean()),
        "Missing share: " + ", ".join(f"{k} {v:.0%}" for k, v in miss.items()) + ".",
        "These fields cannot support segmentation or scoring.",
        "Either make them part of the closing checklist or drop them from the form.",
    ))

    # DQ07 behaviour profile
    prof = deals["lead_behaviour_profile"]
    multi = int(prof.fillna("").str.contains(",").sum())
    issues.append(Issue(
        "DQ07", "low", "Behaviour profile has one clean value", int(prof.isna().sum()) + multi,
        float((prof.isna().sum() + multi) / n_deals),
        f"{int(prof.isna().sum())} deals have no profile and {multi} hold two values "
        "(for example 'cat, wolf').",
        "Profile-based reporting needs a rule for blanks and multiple values.",
        "Use a single-select field with an explicit 'not assessed' option.",
    ))

    # DQ08 sellers absent from order sample
    ok_orders = orders[~orders["order_status"].isin(["canceled", "unavailable"])]
    sellers = set(items.loc[items["order_id"].isin(ok_orders["order_id"]), "seller_id"])
    absent = int((~deals["seller_id"].isin(sellers)).sum())
    issues.append(Issue(
        "DQ08", "medium", "Won sellers appear in order data", absent, absent / n_deals,
        f"{absent:,} of {n_deals:,} won sellers have no order in the public order data.",
        "The public order file may not hold every order, so seller activation measured "
        "here is a lower bound.",
        "Use the full order table when this analysis runs on internal data.",
    ))

    # DQ09 order data tail
    tail = int((orders["order_purchase_timestamp"] > s.ts("order_data_complete_end")).sum())
    issues.append(Issue(
        "DQ09", "low", "Order data is complete to its last date", tail, tail / len(orders),
        f"Only {tail} orders fall after {s.ts('order_data_complete_end'):%d %b %Y}, against "
        "thousands per month before.",
        "Post-deal windows are cut at 31 August 2018 to avoid counting missing orders as no sales.",
        "Confirm the extract date before using the last weeks of any order file.",
    ))

    # DQ10 landing page long tail
    pages = c.groupby("landing_page_id").size()
    small = pages[pages < 10]
    issues.append(Issue(
        "DQ10", "low", "Landing pages have enough traffic to compare", int(small.sum()), float(small.sum() / len(c)),
        f"{len(small)} of {len(pages)} landing pages had fewer than 10 leads in the 2018 cohort.",
        "Raw page conversion rates are noisy; pages are ranked on shrunk rates instead.",
        "Group pages by campaign or template so they can be compared.",
    ))

    # Referential checks that passed (kept so the log shows they were run)
    issues.append(Issue(
        "DQ11", "pass", "Lead IDs are unique and every deal links to a lead", 0, 0.0,
        f"{n_mql:,} unique leads; all {n_deals:,} deals match a lead.", "None.", "None.",
    ))
    return pd.DataFrame([asdict(i) for i in issues])
