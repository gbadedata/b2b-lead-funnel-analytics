"""Write results.json and the generated markdown reports."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


def md_table(df: pd.DataFrame, formats: dict[str, str] | None = None, index: bool = True) -> str:
    formats = formats or {}
    d = df.reset_index() if index else df.copy()
    cols = list(d.columns)
    out = ["| " + " | ".join(str(c).replace("_", " ") for c in cols) + " |",
           "|" + "|".join("---:" if pd.api.types.is_numeric_dtype(d[c]) else "---" for c in cols) + "|"]
    for _, r in d.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)) and np.isnan(v):
                cells.append("")
            elif c in formats:
                cells.append(format(v, formats[c]))
            elif isinstance(v, (bool, np.bool_)):
                cells.append("yes" if v else "no")
            else:
                cells.append(str(v).replace("_", " ") if isinstance(v, str) else str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def _jsonable(o):
    if isinstance(o, pd.DataFrame):
        flat = o.reset_index(drop=isinstance(o.index, pd.RangeIndex) and o.index.name is None)
        return json.loads(flat.to_json(orient="records"))
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, pd.Timestamp):
        return o.strftime("%Y-%m-%d")
    raise TypeError(type(o))


def write_json(results: dict, path: Path) -> None:
    path.write_text(json.dumps(results, indent=2, default=_jsonable))


def write_results_md(r: dict, path: Path) -> None:
    rt = pd.DataFrame(r["channels"]).set_index("origin")
    od = pd.DataFrame(r["odds_ratios"])
    sp = pd.DataFrame(r["speed"]).set_index("origin")
    act = pd.DataFrame(r["deal_quality"]["by_origin"]).set_index("origin")
    lt = pd.DataFrame(r["deal_quality"]["by_lead_type"]).set_index("lead_type")
    sc = r["scoring"]
    met = pd.DataFrame({k: v for k, v in sc["metrics"].items() if k != "base_rate"}).T
    met.index.name = "model"
    pages = pd.DataFrame(r["landing_pages"]["top_shrunk"])
    naive = pd.DataFrame(r["landing_pages"]["top_raw"])
    pct, f3 = ".1%", ".3f"
    s = [
        "# Results (generated)",
        "",
        "This file is written by `make run`. Do not edit by hand.",
        "",
        f"Cohort: {r['cohort']['leads']:,} leads first contacted {r['cohort']['start']} to "
        f"{r['cohort']['end']}; {r['cohort']['wins_90d']:,} won within 90 days "
        f"({r['cohort']['rate_90d']:.1%}).",
        "",
        "## 1. Conversion by source",
        "",
        md_table(rt[["leads", "wins", "rate", "ci_low", "ci_high", "share_of_leads", "share_of_wins", "rankable"]],
                 {"rate": pct, "ci_low": pct, "ci_high": pct, "share_of_leads": pct, "share_of_wins": pct}),
        "",
        f"Chi-square test of independence: chi2 = {r['chi2']['chi2']:.1f}, dof = {r['chi2']['dof']}, "
        f"p = {r['chi2']['p_value']:.1e}.",
        "",
        "### Odds ratios vs organic search, adjusted for contact month",
        "",
        md_table(od[["origin", "odds_ratio", "or_low", "or_high", "p_value", "p_holm", "significant_after_holm"]],
                 {"odds_ratio": ".2f", "or_low": ".2f", "or_high": ".2f", "p_value": ".4f", "p_holm": ".4f"},
                 index=False),
        "",
        "## 2. Speed to close (won within 90 days)",
        "",
        md_table(sp, {"median_days": ".0f", "p75_days": ".0f", "within_14d": ".0%"}),
        "",
        "## 3. Landing pages",
        "",
        f"Pooled page prior: Beta({r['landing_pages']['prior']['alpha']:.2f}, "
        f"{r['landing_pages']['prior']['beta']:.2f}), mean {r['landing_pages']['prior']['prior_mean']:.1%}. "
        f"{r['landing_pages']['pages']} pages in the cohort.",
        "",
        "Top 5 by raw rate (what a naive ranking would show):",
        "",
        md_table(naive, {"raw_rate": pct, "shrunk_rate": pct}, index=False),
        "",
        "Pages with 100+ leads (the ones a decision can rest on):",
        "",
        md_table(pd.DataFrame(r["landing_pages"]["busy_pages"]), {"raw_rate": pct, "shrunk_rate": pct}, index=False),
        "",
        "Top 10 by shrunk rate:",
        "",
        md_table(pages, {"raw_rate": pct, "shrunk_rate": pct, "cred_low": pct, "cred_high": pct}, index=False),
        "",
        "## 4. Lead scoring (train Jan-Mar, test Apr-May)",
        "",
        f"Train: {sc['train']['leads']:,} leads, {sc['train']['rate']:.1%} won. Test: {sc['test']['leads']:,} "
        f"leads, {sc['test']['rate']:.1%} won; {sc['test']['unseen_page_share']:.0%} of test leads came "
        "from landing pages not seen in training.",
        "",
        md_table(met, {c: f3 for c in met.columns}),
        "",
        "Bootstrap 95% intervals (1,000 resamples of the test set):",
        "",
    ]
    for k, v in sc["bootstrap"]["auc_ci"].items():
        s.append(f"- ROC AUC {k}: {v[0]:.3f} to {v[1]:.3f}")
    for k, v in sc["bootstrap"]["auc_diff_vs_channel_only_ci"].items():
        s.append(f"- AUC gain of {k} over source-only: {v[0]:+.3f} to {v[1]:+.3f}")
    s += [
        "",
        "Calibration of the logistic score on the test set (deciles of predicted probability):",
        "",
        md_table(pd.DataFrame(sc["calibration_logistic"]).astype({"bin": int, "leads": int}).set_index("bin"),
                 {"mean_predicted": f3, "observed": f3}),
        "",
        "## 5. After the deal: did the seller start selling?",
        "",
        f"{r['deal_quality']['deals']} deals won by {r['deal_quality']['won_before']} with a full 90-day "
        f"window; {r['deal_quality']['activation_rate']:.1%} made at least one sale in that window in the "
        "public order data (a lower bound, see DQ08).",
        "",
        md_table(act[["deals", "active", "activation_rate", "ci_low", "ci_high", "gmv_per_deal", "share_of_gmv"]],
                 {"activation_rate": pct, "ci_low": pct, "ci_high": pct, "gmv_per_deal": ",.0f",
                  "share_of_gmv": pct}),
        "",
        "By lead type:",
        "",
        md_table(lt[["deals", "active", "activation_rate", "gmv_per_deal", "share_of_gmv"]],
                 {"activation_rate": pct, "gmv_per_deal": ",.0f", "share_of_gmv": pct}),
        "",
    ]
    path.write_text("\n".join(s))


def write_dq_md(issues: pd.DataFrame, path: Path) -> None:
    s = ["# Data quality log (generated)", "",
         "Written for the person who owns the data. Each issue says what was found, why it matters "
         "and what would fix it. Severity: high changes a conclusion; medium limits an analysis; "
         "low is minor or already handled.", ""]
    for _, i in issues.iterrows():
        share = "" if i["share"] is None or pd.isna(i["share"]) else f" ({i['share']:.1%})"
        s += [f"## {i['code']} [{i['severity']}] {i['check']}", "",
              f"- **Affected:** {i['affected']:,}{share}",
              f"- **Finding:** {i['finding']}",
              f"- **Why it matters:** {i['impact']}",
              f"- **Fix:** {i['recommendation']}", ""]
    path.write_text("\n".join(s))
