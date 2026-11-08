"""Static charts for the README and report."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#8a8984"
GRID = "#e4e3df"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]


def _style() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
        "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False, "font.size": 10,
        "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "lines.linewidth": 2, "legend.frameon": False,
    })


def _pct(ax, axis: str = "y") -> None:
    fmt = matplotlib.ticker.PercentFormatter(1.0, decimals=0)
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


def tracking_coverage(monthly: pd.DataFrame, cohort_start: str, path: Path) -> None:
    _style()
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 5.2), sharex=True, gridspec_kw={"height_ratios": [1, 1.2]})
    x = np.arange(len(monthly))
    a1.bar(x, monthly["leads"], color=SERIES[0], width=0.7)
    a1.set_title("Leads per month, and conversion by month of first contact")
    a1.set_ylabel("Leads")
    a2.plot(x, monthly["rate_any"], marker="o", markersize=6, color=SERIES[0])
    cut = list(monthly.index).index(pd.Timestamp(cohort_start).strftime("%Y-%m"))
    for a in (a1, a2):
        a.axvspan(-0.5, cut - 0.5, color=GRID, alpha=0.6, lw=0)
    a2.text(cut / 2 - 0.5, monthly["rate_any"].max() * 0.95, "No deal records\nbefore Dec 2017",
            ha="center", va="top", color=INK2, fontsize=9)
    a2.set_ylabel("Leads won (any time)")
    _pct(a2)
    a2.set_xticks(x, [pd.Timestamp(m).strftime("%b %y") for m in monthly.index], rotation=0, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def channel_conversion(rt: pd.DataFrame, overall: float, path: Path) -> None:
    _style()
    d = rt.sort_values("rate")
    fig, ax = plt.subplots(figsize=(8, 4.8))
    y = np.arange(len(d))
    for i, (_, r) in enumerate(d.iterrows()):
        solid = bool(r["rankable"])
        ax.plot([r["ci_low"], r["ci_high"]], [i, i], color=SERIES[0] if solid else MUTED, lw=2)
        ax.plot(r["rate"], i, "o", ms=8, color=SERIES[0] if solid else SURFACE,
                markeredgecolor=SERIES[0] if solid else MUTED, markeredgewidth=2)
        ax.text(r["ci_high"] + 0.006, i, f"{r['rate']:.1%}  (n={int(r['leads']):,})", va="center",
                fontsize=8.5, color=INK2, bbox=dict(facecolor=SURFACE, edgecolor="none", pad=0.5))
    ax.axvline(overall, color=INK2, lw=1, ls="--", zorder=0)
    ax.text(overall, -0.9, f" overall {overall:.1%}", color=INK2, fontsize=8.5, va="center")
    ax.set_ylim(-1.3, len(d) - 0.5)
    ax.set_yticks(y, [n.replace("_", " ") for n in d.index])
    ax.set_xlim(0, max(d["ci_high"].max() + 0.12, 0.3))
    _pct(ax, "x")
    ax.set_xlabel("Leads won within 90 days of first contact (95% interval)")
    ax.set_title("Conversion by lead source, Jan to May 2018 leads")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.text(0.01, 0.01, "Hollow markers: fewer than 100 leads, shown but not ranked.", fontsize=8, color=MUTED)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def landing_pages(lp: pd.DataFrame, prior_mean: float, path: Path) -> None:
    _style()
    fig, ax = plt.subplots(figsize=(8, 4.6))
    jitter = np.random.default_rng(0).uniform(-0.06, 0.06, len(lp))
    x = lp["leads"].to_numpy() * np.exp(jitter)
    ax.scatter(x, lp["raw_rate"], s=22, facecolors="none", edgecolors=MUTED, lw=1, label="Raw rate")
    ax.scatter(x, lp["shrunk_rate"], s=22, color=SERIES[0], label="Shrunk rate")
    ax.axhline(prior_mean, color=INK2, lw=1, ls="--")
    ax.text(lp["leads"].max(), prior_mean, f"average page rate (prior) {prior_mean:.1%} ", ha="right", va="bottom",
            fontsize=8.5, color=INK2)
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    _pct(ax)
    ax.set_xlabel("Leads per landing page (log scale)")
    ax.set_ylabel("Won within 90 days")
    ax.set_title("Landing pages: small pages swing to 0% or 100% until shrunk")
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def time_to_close(curves: pd.DataFrame, order: list[str], path: Path) -> None:
    _style()
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for i, name in enumerate(order):
        ax.plot(curves.index, curves[name], color=SERIES[i], label=name.replace("_", " "))
    ax.axvline(14, color=MUTED, lw=1, ls=":")
    ax.text(14.8, 0.003, "14 days", color=MUTED, fontsize=8.5, va="bottom")
    ax.set_xlim(0, 92)
    ax.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(0.05))
    _pct(ax)
    ax.set_xlabel("Days since first contact")
    ax.set_ylabel("Share of leads won so far")
    ax.set_title("How fast each source converts (sources with 100+ leads)")
    ax.legend(loc="lower right", ncol=2)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def scoring(y: np.ndarray, scores: dict[str, np.ndarray], calib: pd.DataFrame, path: Path) -> None:
    _style()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.5, 4.3))
    frac = np.linspace(0, 1, 101)
    a1.plot(frac, frac, color=MUTED, lw=1, ls="--", label="random order")
    names = {"logistic": "lead score", "channel_only": "source only"}
    for i, (k, s) in enumerate(scores.items()):
        order = np.argsort(-s, kind="stable")
        cum = np.cumsum(y[order]) / y.sum()
        xs = np.arange(1, len(y) + 1) / len(y)
        a1.plot(xs, cum, color=SERIES[i], label=names.get(k, k))
    a1.axvline(0.3, color=MUTED, lw=1, ls=":")
    _pct(a1)
    _pct(a1, "x")
    a1.set_xlabel("Share of leads called, best scores first")
    a1.set_ylabel("Share of 90-day wins reached")
    a1.set_title("Gains on Apr-May 2018 leads")
    a1.legend(loc="lower right")
    m = max(calib["mean_predicted"].max(), calib["observed"].max()) * 1.1
    a2.plot([0, m], [0, m], color=MUTED, lw=1, ls="--")
    a2.plot(calib["mean_predicted"], calib["observed"], "o-", color=SERIES[0], ms=7)
    _pct(a2)
    _pct(a2, "x")
    a2.set_xlabel("Predicted (score decile mean)")
    a2.set_ylabel("Observed")
    a2.set_title("Calibration of the lead score")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def deal_activation(act: pd.DataFrame, path: Path) -> None:
    _style()
    d = act[act["rankable"]].sort_values("activation_rate")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.5, 3.8), sharey=True)
    y = np.arange(len(d))
    for i, (_, r) in enumerate(d.iterrows()):
        a1.plot([r["ci_low"], r["ci_high"]], [i, i], color=SERIES[0])
        a1.plot(r["activation_rate"], i, "o", ms=8, color=SERIES[0])
    a1.set_yticks(y, [f"{n.replace('_', ' ')} ({int(k)})" for n, k in zip(d.index, d["deals"], strict=True)])
    a1.set_xlim(0, 1)
    _pct(a1, "x")
    a1.set_xlabel("Sold within 90 days of the deal (95% interval)")
    a1.set_title("Won sellers who started selling")
    a2.barh(y, d["gmv_per_deal"], color=SERIES[0], height=0.55)
    for i, v in enumerate(d["gmv_per_deal"]):
        a2.text(v, i, f" R${v:,.0f}", va="center", fontsize=8.5, color=INK2)
    a2.set_xlabel("Order value per won deal, first 90 days (R$)")
    a2.set_title("Value per deal")
    a2.set_xlim(0, d["gmv_per_deal"].max() * 1.3)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
