"""Load Phase 1 CSVs and compute display metrics for charts and the case study."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.settings import OUTPUT_DIR


def _read_csv(name: str) -> pd.DataFrame:
    path = OUTPUT_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run `python build.py` before generating the report."
        )
    df = pd.read_csv(path)
    if "month_start" in df.columns:
        df["month_start"] = pd.to_datetime(df["month_start"])
    return df


def money(value: float, decimals: int = 0) -> str:
    if decimals == 0:
        return f"${value:,.0f}"
    return f"${value:,.{decimals}f}"


def k_money(value: float) -> str:
    if abs(value) >= 1000:
        return f"${value / 1000:,.1f}k"
    return money(value)


def pct(value: float, decimals: int = 1) -> str:
    return f"{value * 100:.{decimals}f}%"


def month_label(ts) -> str:
    return pd.Timestamp(ts).strftime("%b %Y")


@dataclass
class ReportMetrics:
    as_of_date: str
    start_month: pd.Timestamp
    end_month: pd.Timestamp
    ending_mrr: float
    ending_arr: float
    peak_arr: float
    peak_arr_month: pd.Timestamp
    mean_nrr: float
    mean_grr: float
    aug_nrr: float
    nrr_months_above_1: int
    mean_payback: float
    latest_arpu: float
    may_arpu: float
    ending_customers: int
    total_new_mrr: float
    total_expansion_mrr: float
    total_reactivation_mrr: float
    total_contraction_mrr: float
    total_churn_mrr: float
    period_beg_arr: float
    period_new_arr: float
    period_expansion_arr: float
    period_reactivation_arr: float
    period_contraction_arr: float
    period_churn_arr: float
    period_end_arr: float
    kpi: pd.DataFrame
    bridge: pd.DataFrame
    channel: pd.DataFrame
    channel_summary: pd.DataFrame


def load_report_metrics() -> ReportMetrics:
    kpi = _read_csv("kpi_monthly.csv")
    bridge = _read_csv("mrr_bridge.csv")
    channel = _read_csv("channel_metrics.csv")
    assumptions = _read_csv("assumptions.csv")
    as_of = str(assumptions["as_of_date"].iloc[0])

    valid_nrr = kpi.dropna(subset=["nrr"])
    peak_idx = kpi["arr"].idxmax()
    last = kpi.iloc[-1]
    may = kpi.loc[kpi["month_start"] == "2025-05-01"].iloc[0]
    aug = kpi.loc[kpi["month_start"] == "2025-08-01"].iloc[0]

    # Reversal-window bridge: April–September 2025.
    period = bridge[
        (bridge["month_start"] >= "2025-04-01")
        & (bridge["month_start"] <= "2025-09-01")
    ].copy()
    if period.empty:
        raise ValueError("April–September 2025 is missing from mrr_bridge.csv")

    acquired = (
        channel.groupby("acquisition_channel", as_index=False)
        .agg(
            new_customers=("new_customers", "sum"),
            total_cac=("total_cac", "sum"),
        )
    )
    latest_ch = channel.loc[channel["month_start"] == kpi["month_start"].max()].copy()
    channel_summary = acquired.merge(
        latest_ch[
            [
                "acquisition_channel",
                "ch_arpu",
                "ch_active_customers",
                "ch_arr",
            ]
        ],
        on="acquisition_channel",
        how="left",
    )
    gm = float(assumptions["gross_margin"].iloc[0])
    channel_summary["avg_cac"] = (
        channel_summary["total_cac"] / channel_summary["new_customers"]
    )
    channel_summary["payback_proxy"] = channel_summary["avg_cac"] / (
        channel_summary["ch_arpu"] * gm
    )
    channel_summary = channel_summary.sort_values("new_customers", ascending=False)

    return ReportMetrics(
        as_of_date=as_of,
        start_month=kpi["month_start"].min(),
        end_month=kpi["month_start"].max(),
        ending_mrr=float(last["mrr"]),
        ending_arr=float(last["arr"]),
        peak_arr=float(kpi.loc[peak_idx, "arr"]),
        peak_arr_month=kpi.loc[peak_idx, "month_start"],
        mean_nrr=float(valid_nrr["nrr"].mean()),
        mean_grr=float(valid_nrr["grr"].mean()),
        aug_nrr=float(aug["nrr"]),
        nrr_months_above_1=int((valid_nrr["nrr"] > 1.0000001).sum()),
        mean_payback=float(kpi["payback_months"].dropna().mean()),
        latest_arpu=float(last["arpu"]),
        may_arpu=float(may["arpu"]),
        ending_customers=int(last["active_customers"]),
        total_new_mrr=float(bridge["new_mrr"].sum()),
        total_expansion_mrr=float(bridge["expansion_mrr"].sum()),
        total_reactivation_mrr=float(bridge["reactivation_mrr"].sum()),
        total_contraction_mrr=float(bridge["contraction_mrr"].sum()),
        total_churn_mrr=float(bridge["churn_mrr"].sum()),
        period_beg_arr=float(period.iloc[0]["beg_arr"]),
        period_new_arr=float(period["new_arr"].sum()),
        period_expansion_arr=float(period["expansion_arr"].sum()),
        period_reactivation_arr=float(period["reactivation_arr"].sum()),
        period_contraction_arr=float(period["contraction_arr"].sum()),
        period_churn_arr=float(period["churn_arr"].sum()),
        period_end_arr=float(period.iloc[-1]["end_arr"]),
        kpi=kpi,
        bridge=bridge,
        channel=channel,
        channel_summary=channel_summary,
    )
