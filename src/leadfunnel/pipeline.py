"""End-to-end run: python -m leadfunnel.pipeline [--download]"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

from . import deal_quality, excel_pack, figures, funnel, quality, recalc, report, scoring
from .config import SETTINGS, Settings
from .download import ROOT, fetch
from .load import load


def run(raw_dir: Path, out: Path, s: Settings = SETTINGS, make_excel: bool = True) -> dict:
    warnings.filterwarnings("ignore", category=FutureWarning)
    for sub in ("reports", "figures", "outputs"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    raw = load(raw_dir)
    leads = funnel.build_leads(raw.mql, raw.deals, s)
    issues = quality.run_checks(raw, leads, s)
    c = funnel.cohort(leads, s)

    rt = funnel.rate_table(c, "origin", s=s)
    odds = funnel.adjusted_odds_ratios(c)
    pages, prior = funnel.landing_page_table(c)
    speed = funnel.speed_table(c)
    curves = funnel.cumulative_conversion(c, max_days=s.window_days)
    monthly = funnel.monthly_table(leads)
    sc = scoring.run(c, s)
    won = c[c["won_90d"]]
    act = deal_quality.seller_activity(won, raw.orders, raw.items, s)
    by_origin = deal_quality.activity_by(act, "origin", s)
    by_type = deal_quality.activity_by(act, "lead_type", s)

    pre = leads[leads["first_contact_date"] < s.ts("cohort_start")]
    ua = c["unattributed"]
    results = {
        "settings": s.__dict__,
        "cohort": {
            "start": s.cohort_start, "end": s.cohort_end, "leads": len(c),
            "wins_90d": int(c["won_90d"].sum()), "rate_90d": float(c["won_90d"].mean()),
            "wins_any": int(c["won_any"].sum()),
        },
        "coverage": {
            "all_leads": len(leads), "all_deals": len(raw.deals),
            "first_won_date": raw.deals["won_date"].min(),
            "first_contact_min": leads["first_contact_date"].min(),
            "pre_cohort_leads": len(pre), "pre_cohort_rate_any": float(pre["won_any"].mean()),
            "cohort_rate_any": float(c["won_any"].mean()),
        },
        "monthly": monthly,
        "channels": rt,
        "chi2": funnel.channel_independence_test(c),
        "odds_ratios": odds,
        "unattributed": {
            "leads": int(ua.sum()), "share_of_leads": float(ua.mean()),
            "rate": float(c.loc[ua, "won_90d"].mean()), "rate_attributed": float(c.loc[~ua, "won_90d"].mean()),
            "share_of_wins": float(c.loc[ua, "won_90d"].sum() / c["won_90d"].sum()),
        },
        "speed": speed,
        "speed_overall": {
            "median_days": float(won["days_to_close"].median()),
            "within_14d": float((won["days_to_close"] <= 14).mean()),
        },
        "landing_pages": {
            "pages": int(len(pages)), "prior": prior,
            "pages_under_10_leads": int((pages["leads"] < 10).sum()),
            "top3_share_of_leads": float(pages.sort_values("leads", ascending=False)["leads"].head(3).sum() / len(c)),
            "top_shrunk": pages.head(10)[["page", "leads", "wins", "raw_rate", "shrunk_rate", "cred_low",
                                          "cred_high"]].reset_index(drop=True),
            "top_raw": pages.sort_values(["raw_rate", "leads"], ascending=False).head(5)[
                ["page", "leads", "wins", "raw_rate", "shrunk_rate"]].reset_index(drop=True),
            "busy_pages": pages[pages["leads"] >= 100].sort_values("leads", ascending=False)[
                ["page", "leads", "wins", "raw_rate", "shrunk_rate"]].reset_index(drop=True),
        },
        "scoring": {k: v for k, v in sc.items() if k != "scored_test"},
        "deal_quality": {
            "deals": len(act), "won_before": s.deal_quality_won_end,
            "activation_rate": float(act["active_90d"].mean()),
            "by_origin": by_origin, "by_lead_type": by_type,
        },
        "data_quality": issues,
    }

    figures.tracking_coverage(monthly, s.cohort_start, out / "figures" / "01_deal_tracking_coverage.png")
    figures.channel_conversion(rt, float(c["won_90d"].mean()), out / "figures" / "02_conversion_by_source.png")
    figures.landing_pages(pages, prior["prior_mean"], out / "figures" / "03_landing_page_shrinkage.png")
    big = [o for o in rt.index if rt.loc[o, "rankable"]][:5]
    figures.time_to_close(curves, big, out / "figures" / "04_time_to_close.png")
    test = sc["scored_test"]
    yte = test["won_90d"].astype(int).to_numpy()
    figures.scoring(yte, {"logistic": test["score"].to_numpy(), "channel_only": test["source_only_score"].to_numpy()},
                    sc["calibration_logistic"], out / "figures" / "05_lead_score_gains.png")
    figures.deal_activation(by_origin, out / "figures" / "06_post_deal_activation.png")

    if make_excel:
        xlsx = excel_pack.build(c, rt, odds, pages, issues, test, out / "outputs" / "lead_funnel_pack.xlsx")
        if recalc.available():
            res = recalc.recalc(xlsx)
            if res["errors"]:
                raise RuntimeError(f"formula errors in workbook: {res['errors'][:5]}")
            results["workbook"] = {"formulas": res["total_formulas"], "errors": 0}
    report.write_json(results, out / "reports" / "results.json")
    report.write_results_md(json.loads((out / "reports" / "results.json").read_text()),
                            out / "reports" / "RESULTS.md")
    report.write_dq_md(issues, out / "reports" / "DATA_QUALITY.md")
    test.to_csv(out / "outputs" / "lead_scores_apr_may_2018.csv", index=False)
    return results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true", help="fetch and verify the data first")
    ap.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw")
    ap.add_argument("--out", type=Path, default=ROOT)
    a = ap.parse_args()
    if a.download:
        fetch(a.raw_dir)
    r = run(a.raw_dir, a.out)
    print(f"cohort {r['cohort']['leads']} leads, {r['cohort']['rate_90d']:.1%} won in 90 days; "
          f"lead score AUC {r['scoring']['metrics']['logistic']['roc_auc']:.3f}")


if __name__ == "__main__":
    main()
