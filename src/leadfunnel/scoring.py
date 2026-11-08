"""Lead scoring from what is known at first contact.

Only fields available when the enquiry arrives are used (channel, landing page,
weekday). Everything on the closed-deal record is an outcome and is excluded.
The split is by time: train on January to March, test once on April and May.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler

from .config import SETTINGS, UNATTRIBUTED, Settings


def time_split(df: pd.DataFrame, s: Settings = SETTINGS) -> tuple[pd.DataFrame, pd.DataFrame]:
    cut = s.ts("train_end")
    return df[df["first_contact_date"] <= cut].copy(), df[df["first_contact_date"] > cut].copy()


def smoothed_rate(wins: pd.Series, n: pd.Series, prior: float, m: float) -> pd.Series:
    return (wins + m * prior) / (n + m)


def target_encode(
    train: pd.DataFrame, test: pd.DataFrame, col: str, y: str, m: float, seed: int, folds: int = 5
) -> tuple[np.ndarray, np.ndarray]:
    """Smoothed target encoding: out-of-fold on train, full-train stats on test.

    Out-of-fold means a training lead never sees its own outcome, which would
    otherwise make single-lead pages look perfectly predictive.
    """
    prior = float(train[y].mean())
    tr = np.empty(len(train))
    kf = KFold(n_splits=folds, shuffle=True, random_state=seed)
    for fit_idx, enc_idx in kf.split(train):
        fit = train.iloc[fit_idx]
        stats_ = fit.groupby(col)[y].agg(["sum", "size"])
        rate = smoothed_rate(stats_["sum"], stats_["size"], prior, m)
        tr[enc_idx] = train.iloc[enc_idx][col].map(rate).fillna(prior).to_numpy()
    full = train.groupby(col)[y].agg(["sum", "size"])
    rate = smoothed_rate(full["sum"], full["size"], prior, m)
    te = test[col].map(rate).fillna(prior).to_numpy()
    return tr, te


def group_origins(train: pd.DataFrame, test: pd.DataFrame, min_n: int) -> tuple[pd.Series, pd.Series]:
    """Model-ready source groups.

    Blank and 'unknown' sources are both unattributed, so they share one level.
    Sources with fewer than ``min_n`` training leads are pooled, because a
    handful of leads cannot support their own coefficient.
    """
    def base(o: pd.Series) -> pd.Series:
        return o.where(~o.isin(UNATTRIBUTED), "unattributed")

    tr, te = base(train["origin"]), base(test["origin"])
    counts = tr.value_counts()
    keep = set(counts[counts >= min_n].index)
    return tr.where(tr.isin(keep), "other_small"), te.where(te.isin(keep), "other_small")


def make_features(train: pd.DataFrame, test: pd.DataFrame, s: Settings = SETTINGS) -> tuple[pd.DataFrame, pd.DataFrame]:
    y = "won_90d"
    tr_y = train.assign(won_90d=train[y].astype(int))
    te_tr, te_te = target_encode(tr_y, test, "landing_page_id", y, s.te_smoothing, s.seed)
    vol = train["landing_page_id"].value_counts()
    g_tr, g_te = group_origins(train, test, s.min_n_rank)
    origins = sorted(g_tr.unique())

    def build(df: pd.DataFrame, te: np.ndarray, grp: pd.Series) -> pd.DataFrame:
        X = pd.DataFrame(index=df.index)
        for o in origins:
            X[f"source={o}"] = (grp == o).astype(float)
        for d in range(7):
            X[f"weekday={d}"] = (df["weekday"] == d).astype(float)
        X["page_rate_te"] = te
        X["page_log_volume"] = np.log1p(df["landing_page_id"].map(vol).fillna(0).to_numpy())
        X["page_unseen"] = (~df["landing_page_id"].isin(vol.index)).astype(float)
        return X

    return build(train, te_tr, g_tr), build(test, te_te, g_te)


def gains(y: np.ndarray, score: np.ndarray, fractions=(0.1, 0.2, 0.3, 0.5)) -> dict[str, float]:
    """Share of all wins found in the top fraction of leads ranked by score."""
    order = np.argsort(-score, kind="stable")
    y_sorted = np.asarray(y)[order]
    total = y_sorted.sum()
    out = {}
    for f in fractions:
        k = int(round(f * len(y_sorted)))
        out[f"top_{int(f * 100)}pct"] = float(y_sorted[:k].sum() / total) if total else float("nan")
    return out


def metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return {
        "roc_auc": float(roc_auc_score(y, p)),
        "pr_auc": float(average_precision_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p)),
        **gains(y, p),
    }


def bootstrap_auc(y: np.ndarray, scores: dict[str, np.ndarray], ref: str, reps: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    n = len(y)
    draws = {k: [] for k in scores}
    diffs = {k: [] for k in scores if k != ref}
    for _ in range(reps):
        idx = rng.integers(0, n, n)
        if y[idx].min() == y[idx].max():
            continue
        aucs = {k: roc_auc_score(y[idx], v[idx]) for k, v in scores.items()}
        for k, a in aucs.items():
            draws[k].append(a)
        for k in diffs:
            diffs[k].append(aucs[k] - aucs[ref])
    ci = lambda a: [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]
    return {
        "auc_ci": {k: ci(v) for k, v in draws.items()},
        f"auc_diff_vs_{ref}_ci": {k: ci(v) for k, v in diffs.items()},
    }


def calibration_table(y: np.ndarray, p: np.ndarray, bins: int = 10) -> pd.DataFrame:
    q = pd.qcut(pd.Series(p).rank(method="first"), bins, labels=False)
    df = pd.DataFrame({"bin": q + 1, "p": p, "y": y})
    g = df.groupby("bin").agg(leads=("y", "size"), mean_predicted=("p", "mean"), observed=("y", "mean"))
    return g


def run(cohort_df: pd.DataFrame, s: Settings = SETTINGS) -> dict:
    train, test = time_split(cohort_df, s)
    Xtr, Xte = make_features(train, test, s)
    ytr = train["won_90d"].astype(int).to_numpy()
    yte = test["won_90d"].astype(int).to_numpy()

    base = np.full(len(test), ytr.mean())
    g_tr, g_te = group_origins(train, test, s.min_n_rank)
    ch = train["won_90d"].groupby(g_tr).mean()
    channel_only = g_te.map(ch).fillna(ytr.mean()).to_numpy()

    scaler = StandardScaler().fit(Xtr)
    lr = LogisticRegression(max_iter=2000, C=1.0).fit(scaler.transform(Xtr), ytr)
    p_lr = lr.predict_proba(scaler.transform(Xte))[:, 1]

    # Ablation: the same model without landing-page features.
    no_page = [c for c in Xtr.columns if not c.startswith("page_")]
    sc_np = StandardScaler().fit(Xtr[no_page])
    lr_np = LogisticRegression(max_iter=2000, C=1.0).fit(sc_np.transform(Xtr[no_page]), ytr)
    p_np = lr_np.predict_proba(sc_np.transform(Xte[no_page]))[:, 1]

    hgb = HistGradientBoostingClassifier(
        max_depth=3, learning_rate=0.05, max_iter=200, l2_regularization=1.0,
        min_samples_leaf=40, random_state=s.seed,
    ).fit(Xtr, ytr)
    p_hgb = hgb.predict_proba(Xte)[:, 1]

    scores = {"base_rate": base, "channel_only": channel_only, "logistic_without_page": p_np,
              "logistic": p_lr, "gradient_boosting": p_hgb}
    res = {
        "train": {"leads": int(len(train)), "wins": int(ytr.sum()), "rate": float(ytr.mean()),
                  "first": f"{train['first_contact_date'].min():%Y-%m-%d}",
                  "last": f"{train['first_contact_date'].max():%Y-%m-%d}"},
        "test": {"leads": int(len(test)), "wins": int(yte.sum()), "rate": float(yte.mean()),
                 "first": f"{test['first_contact_date'].min():%Y-%m-%d}",
                 "last": f"{test['first_contact_date'].max():%Y-%m-%d}",
                 "unseen_page_share": float(Xte["page_unseen"].mean())},
        "metrics": {k: (metrics(yte, v) if k != "base_rate" else
                        {"brier": float(brier_score_loss(yte, v)), "log_loss": float(log_loss(yte, v))})
                    for k, v in scores.items()},
        "bootstrap": bootstrap_auc(yte, {k: v for k, v in scores.items() if k != "base_rate"},
                                   "channel_only", s.bootstrap_reps, s.seed),
        "logistic_coefficients": dict(zip(Xtr.columns, map(float, lr.coef_[0]), strict=True)),
    }
    scored = test[["mql_id", "first_contact_date", "origin", "landing_page_id", "won_90d"]].copy()
    scored["source_only_score"] = channel_only
    scored["score"] = p_lr
    scored["decile"] = pd.qcut(scored["score"].rank(method="first", ascending=False), 10, labels=False) + 1
    res["calibration_logistic"] = calibration_table(yte, p_lr)
    res["scored_test"] = scored
    return res
