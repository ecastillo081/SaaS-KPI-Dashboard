"""Generate print-ready charts from validated Phase 1 CSVs."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

from src.report_metrics import ReportMetrics, load_report_metrics, month_label, money, pct
from src.settings import OUTPUT_DIR

CHART_DIR = OUTPUT_DIR / "charts"

INK = "#1a2332"
ACCENT = "#1f4e79"
MUTED = "#5a6575"
SOFT = "#f4f6f9"
LINE = "#d8dee8"
NEW = "#1f4e79"
REACT = "#3d6e6e"
CHURN = "#8c3d3d"
ZERO = "#9aa3b0"
ENDING = "#1a2332"
GRID = "#e6ebf1"


def _style_axes(ax, ylabel: str) -> None:
    ax.set_facecolor("white")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(LINE)
    ax.spines["bottom"].set_color(LINE)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.set_ylabel(ylabel, color=INK, fontsize=9)
    ax.yaxis.label.set_color(INK)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def _quarter_ticks(ax, dates: pd.Series) -> None:
    ticks = [d for d in dates if d.month in (1, 4, 7, 10) or d == dates.max()]
    ax.set_xticks(ticks)
    ax.set_xticklabels([d.strftime("%b\n%Y") for d in ticks], fontsize=7)
    ax.set_xlim(dates.min(), dates.max())


def _save(fig: plt.Figure, name: str) -> Path:
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    path = CHART_DIR / name
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def plot_arr_trend(m: ReportMetrics) -> Path:
    fig, ax = plt.subplots(figsize=(7.4, 2.55))
    x = m.kpi["month_start"]
    y = m.kpi["arr"]
    ax.plot(x, y, color=ACCENT, linewidth=2.2, zorder=3)
    ax.fill_between(x, y, color=ACCENT, alpha=0.08, zorder=2)
    peak_x = m.peak_arr_month
    peak_y = m.peak_arr
    end_x = m.end_month
    end_y = m.ending_arr
    ax.scatter([peak_x, end_x], [peak_y, end_y], color=ACCENT, s=22, zorder=4)
    ax.annotate(
        f"Peak {money(peak_y)}\n{month_label(peak_x)}",
        xy=(peak_x, peak_y),
        xytext=(8, 10),
        textcoords="offset points",
        fontsize=8,
        color=INK,
        fontweight="bold",
    )
    ax.annotate(
        f"Ending {money(end_y)}",
        xy=(end_x, end_y),
        xytext=(-78, -22),
        textcoords="offset points",
        fontsize=8,
        color=INK,
        fontweight="bold",
    )
    _style_axes(ax, "Run-rate ARR ($)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v/1000:.0f}k"))
    ax.set_xlim(x.min(), x.max())
    ax.set_ylim(0, peak_y * 1.18)
    fig.tight_layout()
    return _save(fig, "arr_trend.png")


def plot_arr_bridge(m: ReportMetrics) -> Path:
    labels = [
        "Beginning",
        "New",
        "Expansion",
        "Reactivation",
        "Contraction",
        "Churn",
        "Ending",
    ]
    deltas = [
        m.period_beg_arr,
        m.period_new_arr,
        m.period_expansion_arr,
        m.period_reactivation_arr,
        -m.period_contraction_arr,
        -m.period_churn_arr,
        m.period_end_arr,
    ]
    colors = [ACCENT, NEW, ZERO, REACT, ZERO, CHURN, ENDING]
    running = m.period_beg_arr
    bases = [0.0]
    heights = [m.period_beg_arr]
    for i, delta in enumerate(deltas[1:-1], start=1):
        if delta >= 0:
            bases.append(running)
            heights.append(delta)
            running += delta
        else:
            running += delta
            bases.append(running)
            heights.append(-delta)
    bases.append(0.0)
    heights.append(m.period_end_arr)

    fig, ax = plt.subplots(figsize=(7.4, 2.7))
    x = np.arange(len(labels))
    draw_heights = [h if h > 0 else 0.0 for h in heights]
    bars = ax.bar(x, draw_heights, bottom=bases, color=colors, width=0.62, zorder=3)
    for i in range(len(labels) - 1):
        top = bases[i] + draw_heights[i]
        ax.plot([i + 0.31, i + 0.69], [top, top], color=LINE, linewidth=0.9, zorder=2)

    for i, (bar, raw) in enumerate(zip(bars, deltas)):
        if abs(raw) < 1:
            y = bases[i]
            ax.plot([i - 0.18, i + 0.18], [y, y], color=ZERO, linewidth=2.2, zorder=4)
            ax.text(
                i,
                y + (m.period_end_arr * 0.03),
                "$0",
                ha="center",
                va="bottom",
                fontsize=7.5,
                color=MUTED,
            )
            continue
        label = money(abs(raw)) if raw >= 0 else f"−{money(abs(raw))}"
        y = bases[i] + draw_heights[i]
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            y + (m.period_end_arr * 0.02),
            label,
            ha="center",
            va="bottom",
            fontsize=7.5,
            color=INK,
            fontweight="bold",
        )

    _style_axes(ax, "Run-rate ARR ($)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v/1000:.0f}k"))
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ymax = max(m.period_beg_arr + m.period_new_arr, m.period_end_arr) * 1.18
    ax.set_ylim(0, ymax)
    fig.tight_layout()
    return _save(fig, "arr_bridge.png")


def plot_nrr_grr(m: ReportMetrics) -> Path:
    df = m.kpi.dropna(subset=["nrr"]).copy()
    fig, ax = plt.subplots(figsize=(7.4, 2.45))
    ax.axhline(1.0, color=MUTED, linewidth=1.0, linestyle="--", zorder=1)
    ax.plot(df["month_start"], df["nrr"], color=ACCENT, linewidth=2.2, label="NRR / GRR", zorder=3)
    ax.scatter(
        [pd.Timestamp("2025-08-01")],
        [m.aug_nrr],
        color=CHURN,
        s=26,
        zorder=4,
    )
    ax.annotate(
        f"Aug 2025  {pct(m.aug_nrr)}",
        xy=(pd.Timestamp("2025-08-01"), m.aug_nrr),
        xytext=(-30, -28),
        textcoords="offset points",
        fontsize=8,
        color=CHURN,
        fontweight="bold",
    )
    ax.annotate(
        "100% line",
        xy=(df["month_start"].iloc[2], 1.0),
        xytext=(0, 6),
        textcoords="offset points",
        fontsize=7.5,
        color=MUTED,
    )
    _style_axes(ax, "Retention rate")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0, decimals=0))
    ax.set_ylim(0.75, 1.08)
    ax.set_xlim(df["month_start"].min(), df["month_start"].max())
    fig.tight_layout()
    return _save(fig, "nrr_grr.png")


def plot_active_customers(m: ReportMetrics) -> Path:
    fig, ax = plt.subplots(figsize=(7.4, 2.15))
    ax.plot(m.kpi["month_start"], m.kpi["active_customers"], color=ACCENT, linewidth=2.2, zorder=3)
    ax.fill_between(m.kpi["month_start"], m.kpi["active_customers"], color=ACCENT, alpha=0.08)
    last_x = m.end_month
    last_y = m.ending_customers
    ax.scatter([last_x], [last_y], color=ACCENT, s=22, zorder=4)
    ax.annotate(
        f"{last_y} active logos",
        xy=(last_x, last_y),
        xytext=(-86, -18),
        textcoords="offset points",
        fontsize=8,
        color=INK,
        fontweight="bold",
    )
    _style_axes(ax, "Active customers")
    ax.set_ylim(0, max(m.kpi["active_customers"]) * 1.18)
    ax.set_xlim(m.kpi["month_start"].min(), m.kpi["month_start"].max())
    fig.tight_layout()
    return _save(fig, "active_customers.png")


def plot_arpu(m: ReportMetrics) -> Path:
    fig, ax = plt.subplots(figsize=(3.65, 2.35))
    ax.plot(m.kpi["month_start"], m.kpi["arpu"], color=ACCENT, linewidth=2.1, zorder=3)
    may_x = pd.Timestamp("2025-05-01")
    ax.scatter([may_x, m.end_month], [m.may_arpu, m.latest_arpu], color=ACCENT, s=18, zorder=4)
    ax.annotate(
        f"May {money(m.may_arpu, 1)}",
        xy=(may_x, m.may_arpu),
        xytext=(-18, 8),
        textcoords="offset points",
        fontsize=7.5,
        color=INK,
    )
    ax.annotate(
        f"Sep {money(m.latest_arpu, 1)}",
        xy=(m.end_month, m.latest_arpu),
        xytext=(-74, -16),
        textcoords="offset points",
        fontsize=7.5,
        color=INK,
    )
    _style_axes(ax, "ARPU ($)")
    _quarter_ticks(ax, m.kpi["month_start"])
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:.0f}"))
    ax.set_ylim(0, max(m.kpi["arpu"]) * 1.22)
    fig.tight_layout()
    return _save(fig, "arpu_trend.png")


def plot_payback(m: ReportMetrics) -> Path:
    df = m.kpi.dropna(subset=["payback_months"]).copy()
    fig, ax = plt.subplots(figsize=(3.65, 2.35))
    ax.plot(df["month_start"], df["payback_months"], color=ACCENT, linewidth=2.1, zorder=3)
    ax.axhline(m.mean_payback, color=CHURN, linewidth=1.0, linestyle="--", zorder=2)
    ax.annotate(
        f"Mean {m.mean_payback:.1f} mo",
        xy=(df["month_start"].iloc[8], m.mean_payback),
        xytext=(6, 6),
        textcoords="offset points",
        fontsize=7.5,
        color=CHURN,
        fontweight="bold",
    )
    _style_axes(ax, "Payback (months)")
    _quarter_ticks(ax, df["month_start"])
    ax.set_ylim(0, max(df["payback_months"]) * 1.15)
    fig.tight_layout()
    return _save(fig, "cac_payback.png")


def generate_charts(metrics: ReportMetrics | None = None) -> list[Path]:
    m = metrics if metrics is not None else load_report_metrics()
    paths = [
        plot_arr_trend(m),
        plot_arr_bridge(m),
        plot_nrr_grr(m),
        plot_active_customers(m),
        plot_arpu(m),
        plot_payback(m),
    ]
    return paths
