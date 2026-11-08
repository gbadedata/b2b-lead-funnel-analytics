"""Lead-level table, cohort definition and funnel statistics."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import optimize, stats

from .config import MISSING_ORIGIN, REFERENCE_ORIGIN, SETTINGS, UNATTRIBUTED, Settings


def wilson(k: np.ndarray | int, n: np.ndarray | int, z: float = 1.96) -> tuple[np.ndarray, np.ndarray]:
    """Wilson score interval for a binomial proportion. Safe for k=0 and k=n."""
    k = np.asarray(k, dtype=float)
    n = np.asarray(n, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        p = np.where(n > 0, k / n, np.nan)
        denom = 1 + z**2 / n
        centre = (p + z**2 / (2 * n)) / denom
        half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return np.clip(centre - half, 0, 1), np.clip(centre + half, 0, 1)


def build_leads(mql: pd.DataFrame, deals: pd.DataFrame, s: Settings = SETTINGS) -> pd.DataFrame:
    """One row per lead, with the deal outcome attached."""
    keep = ["mql_id", "seller_id", "sdr_id", "sr_id", "won_date", "business_segment",
            "lead_type", "business_type", "declared_monthly_revenue"]
    df = mql.merge(deals[keep], on="mql_id", how="left", validate="one_to_one")
    df["origin"] = df["origin"].fillna(MISSING_ORIGIN)
    df["unattributed"] = df["origin"].isin(UNATTRIBUTED)
    df["month"] = df["first_contact_date"].dt.strftime("%Y-%m")
    df["weekday"] = df["first_contact_date"].dt.dayofweek
    df["won_any"] = df["won_date"].notna()
    raw_days = (df["won_date"].dt.normalize() - df["first_contact_date"]).dt.days
    df["won_before_contact"] = raw_days < 0
    # A deal dated before first contact is kept as a same-day win and flagged.
    df["days_to_close"] = raw_days.clip(lower=0)
    df["won_90d"] = df["won_any"] & (df["days_to_close"] <= s.window_days)
    return df


def cohort(leads: pd.DataFrame, s: Settings = SETTINGS) -> pd.DataFrame:
    """Leads first contacted while deal tracking was complete."""
    m = leads["first_contact_date"].between(s.ts("cohort_start"), s.ts("cohort_end"))
    return leads.loc[m].copy()


def rate_table(df: pd.DataFrame, by: str, outcome: str = "won_90d", s: Settings = SETTINGS) -> pd.DataFrame:
    g = df.groupby(by).agg(leads=(outcome, "size"), wins=(outcome, "sum"))
    g["rate"] = g["wins"] / g["leads"]
    g["ci_low"], g["ci_high"] = wilson(g["wins"].to_numpy(), g["leads"].to_numpy())
    g["share_of_leads"] = g["leads"] / g["leads"].sum()
    g["share_of_wins"] = g["wins"] / g["wins"].sum()
    g["rankable"] = g["leads"] >= s.min_n_rank
    return g.sort_values("leads", ascending=False)


def channel_independence_test(df: pd.DataFrame) -> dict:
    tab = pd.crosstab(df["origin"], df["won_90d"])
    chi2, p, dof, _ = stats.chi2_contingency(tab)
    return {"chi2": float(chi2), "dof": int(dof), "p_value": float(p)}


def holm(pvals: np.ndarray) -> np.ndarray:
    """Holm-Bonferroni adjusted p-values."""
    p = np.asarray(pvals, dtype=float)
    order = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, (m - rank) * p[idx])
        adj[idx] = min(1.0, running)
    return adj


def adjusted_odds_ratios(df: pd.DataFrame, reference: str = REFERENCE_ORIGIN) -> pd.DataFrame:
    """Logistic regression of 90-day conversion on channel, holding contact month fixed.

    Month enters as a fixed effect so a channel is not credited for being
    busier in a strong month.
    """
    import statsmodels.formula.api as smf

    d = df.assign(y=df["won_90d"].astype(int))
    formula = f"y ~ C(origin, Treatment(reference='{reference}')) + C(month)"
    fit = smf.logit(formula, data=d).fit(disp=False)
    rows = []
    ci = fit.conf_int()
    for term in fit.params.index:
        if not term.startswith("C(origin"):
            continue
        name = term.split("[T.")[1].rstrip("]")
        rows.append({
            "origin": name,
            "odds_ratio": float(np.exp(fit.params[term])),
            "or_low": float(np.exp(ci.loc[term, 0])),
            "or_high": float(np.exp(ci.loc[term, 1])),
            "p_value": float(fit.pvalues[term]),
        })
    out = pd.DataFrame(rows)
    out["p_holm"] = holm(out["p_value"].to_numpy())
    out["significant_after_holm"] = out["p_holm"] < 0.05
    return out.sort_values("odds_ratio", ascending=False).reset_index(drop=True)


def fit_beta_prior(wins: np.ndarray, n: np.ndarray) -> tuple[float, float]:
    """Beta prior for page conversion rates by maximum marginal (beta-binomial) likelihood."""
    wins = np.asarray(wins)
    n = np.asarray(n)

    def nll(theta: np.ndarray) -> float:
        a, b = np.exp(theta)
        return -stats.betabinom.logpmf(wins, n, a, b).sum()

    p0 = max(wins.sum() / n.sum(), 1e-3)
    res = optimize.minimize(nll, x0=np.log([p0 * 10, (1 - p0) * 10]), method="Nelder-Mead")
    a, b = np.exp(res.x)
    return float(a), float(b)


def landing_page_table(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Raw and shrunk conversion per landing page.

    Shrinkage pulls small pages toward the overall rate, so a page with one
    lead and one win does not top the ranking.
    """
    g = df.groupby("landing_page_id").agg(leads=("won_90d", "size"), wins=("won_90d", "sum"))
    a, b = fit_beta_prior(g["wins"].to_numpy(), g["leads"].to_numpy())
    g["raw_rate"] = g["wins"] / g["leads"]
    pa, pb = a + g["wins"], b + g["leads"] - g["wins"]
    g["shrunk_rate"] = pa / (pa + pb)
    g["cred_low"] = stats.beta.ppf(0.05, pa, pb)
    g["cred_high"] = stats.beta.ppf(0.95, pa, pb)
    g["page"] = [p[:8] for p in g.index]
    prior = {"alpha": a, "beta": b, "prior_mean": a / (a + b)}
    return g.sort_values("shrunk_rate", ascending=False), prior


def cumulative_conversion(df: pd.DataFrame, by: str = "origin", max_days: int = 90) -> pd.DataFrame:
    """Share of each group's leads won within d days of first contact, d = 0..max_days."""
    days = np.arange(max_days + 1)
    rows = {}
    for name, grp in df.groupby(by):
        dtc = grp.loc[grp["won_90d"], "days_to_close"].to_numpy()
        rows[name] = [(dtc <= d).sum() / len(grp) for d in days]
    return pd.DataFrame(rows, index=pd.Index(days, name="days"))


def speed_table(df: pd.DataFrame) -> pd.DataFrame:
    won = df[df["won_90d"]]
    g = won.groupby("origin")["days_to_close"].agg(
        wins="size", median_days="median",
        p75_days=lambda x: float(np.percentile(x, 75)),
        within_14d=lambda x: float((x <= 14).mean()),
    )
    return g.sort_values("wins", ascending=False)


def monthly_table(leads: pd.DataFrame) -> pd.DataFrame:
    g = leads.groupby("month").agg(
        leads=("mql_id", "size"), wins_any=("won_any", "sum"), wins_90d=("won_90d", "sum")
    )
    g["rate_any"] = g["wins_any"] / g["leads"]
    g["rate_90d"] = g["wins_90d"] / g["leads"]
    return g
