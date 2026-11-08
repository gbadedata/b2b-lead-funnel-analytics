"""Analysis settings. Every date and threshold used by the pipeline lives here."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Settings:
    # Deal records start on 2017-12-05, so leads first contacted before 2018
    # cannot show their true conversion. The analysis cohort starts after that.
    cohort_start: str = "2018-01-01"
    cohort_end: str = "2018-05-31"  # last first-contact date in the lead file

    # A lead counts as converted if the deal is won within this many days.
    # Every cohort lead has at least 167 days of deal data after first contact,
    # so a 90-day window is fully observed for all of them.
    window_days: int = 90

    # Lead scoring: train on Jan-Mar first contacts, test once on Apr-May.
    train_end: str = "2018-03-31"

    # Seller activity after the deal: order data thins out after August 2018,
    # so only deals won by 1 June 2018 get a full 90-day post-deal window.
    deal_quality_won_end: str = "2018-06-01"
    order_data_complete_end: str = "2018-08-31"

    # Groups smaller than this are reported but not ranked.
    min_n_rank: int = 100
    # Smoothing weight (in pseudo-leads) for landing-page target encoding.
    te_smoothing: float = 20.0
    bootstrap_reps: int = 1000
    seed: int = 7

    def ts(self, name: str) -> pd.Timestamp:
        return pd.Timestamp(getattr(self, name))


SETTINGS = Settings()

# Origin labels as recorded, plus the label used for blanks.
MISSING_ORIGIN = "missing"
UNATTRIBUTED = {"unknown", MISSING_ORIGIN}
REFERENCE_ORIGIN = "organic_search"
