"""
Generate or update the `invoices` sheet in saas_kpi_seeds.xlsx (Phase 1 / Table 4).

Design:
- Reads `customers` and `subscriptions` (respects FKs and your pricing/edits).
- Emits billing rows for coverage periods.
  * Default cadence: monthly invoices aligned to subscription months.
  * A small percent can be annual prepay (configurable), generating one larger invoice
    that covers 12 months (or the remaining window if shorter).
- Adds rare refunds/credit memos as separate rows (negative amount, `is_refund = TRUE`).
- Active periods are billed only up to the end of the previous month (no future invoices).

Schema:
- invoice_id (PK)      : string like I000001
- customer_id (FK)     : customers.customer_id
- invoice_date         : when the invoice was issued (first day of coverage window)
- amount               : positive for standard invoices; negative for refunds/credit memos
- is_refund            : boolean (FALSE for standard invoice; TRUE for refund/credit)
- period_start         : coverage start date
- period_end           : coverage end date (inclusive)

Run: `python 04_generate_invoices.py`
Requires: pandas, numpy, openpyxl
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
import pandas as pd


@dataclass
class InvoicesConfig:
    workbook_path: str = "../data/saas_kpi_seeds.xlsx"
    customers_sheet: str = "customers"
    subs_sheet: str = "subscriptions"
    invoices_sheet: str = "invoices"
    random_seed: int = 456

    # Billing controls
    pct_annual_prepay: float = 0.08    # ~8% of subs bill annually instead of monthly
    refund_rate: float = 0.03          # ~3% of invoices get a small credit memo
    refund_pct_of_invoice: Tuple[float, float] = (0.05, 0.20)  # 5–20% of that invoice amount


# Helpers

def _month_range(start: pd.Timestamp, end: pd.Timestamp) -> List[pd.Timestamp]:
    """Inclusive list of month starts covering [start, end]."""
    start_m = pd.Timestamp(start).replace(day=1)
    end_m = pd.Timestamp(end).replace(day=1)
    months = []
    cur = start_m
    while cur <= end_m:
        months.append(cur)
        cur = cur + pd.DateOffset(months=1)
    return months


def _coverage_window_for_month(month_start: pd.Timestamp) -> Tuple[pd.Timestamp, pd.Timestamp]:
    month_end = (month_start + pd.DateOffset(months=1) - pd.Timedelta(days=1))
    return month_start, month_end


def _bounded(a: pd.Timestamp, lo: pd.Timestamp, hi: pd.Timestamp) -> pd.Timestamp:
    return max(lo, min(a, hi))


def main():
    cfg = InvoicesConfig()

    if not os.path.exists(cfg.workbook_path):
        raise FileNotFoundError(f"Workbook '{cfg.workbook_path}' not found. Run previous generators first.")

    customers = pd.read_excel(cfg.workbook_path, sheet_name=cfg.customers_sheet, engine="openpyxl")
    subs = pd.read_excel(cfg.workbook_path, sheet_name=cfg.subs_sheet, engine="openpyxl")

    if customers.empty or subs.empty:
        raise ValueError("Required sheets missing or empty.")

    # Ensure datetime
    subs["start_date"] = pd.to_datetime(subs["start_date"])  # not NaT
    # end_date may be NaT; treat active periods specially
    if "end_date" in subs.columns:
        subs["end_date"] = pd.to_datetime(subs["end_date"])  # can be NaT

    rng = np.random.default_rng(cfg.random_seed)

    # Time bound: generate invoices only up to the end of the previous month
    today = pd.Timestamp.today().normalize()
    end_of_prev_month = (today.replace(day=1) - pd.offsets.Day(1))

    invoice_rows: List[dict] = []

    for _, r in subs.iterrows():
        cid = str(r["customer_id"])  # FK
        start = pd.Timestamp(r["start_date"])  # inclusive
        # If end_date is NaT, bound by end_of_prev_month
        raw_end = r["end_date"] if pd.notna(r["end_date"]) else end_of_prev_month
        end = pd.Timestamp(min(pd.Timestamp(raw_end), end_of_prev_month))

        if end < start:
            # Active period may start in current month with no billable history yet
            continue

        price = float(r["price_mrr"])  # from subscriptions

        # Decide cadence: annual prepay or monthly
        is_annual = rng.random() < cfg.pct_annual_prepay

        if is_annual:
            # One invoice covering up to 12 months from start (or bounded by end)
            covered_end = min(start + pd.DateOffset(months=12) - pd.Timedelta(days=1), end)
            period_start = start.normalize()
            period_end = pd.Timestamp(covered_end).normalize()
            months_covered = max(1, (period_end.year - period_start.year) * 12 + (period_end.month - period_start.month) + 1)
            amount = round(price * months_covered, 2)

            invoice_rows.append({
                "customer_id": cid,
                "invoice_date": period_start.date(),
                "amount": amount,
                "is_refund": False,
                "period_start": period_start.date(),
                "period_end": period_end.date(),
            })
        else:
            # Monthly cadence: one invoice per month in [start, end]
            for m0 in _month_range(start, end):
                cov_start, cov_end = _coverage_window_for_month(m0)
                # Clip to subscription window
                period_start = _bounded(cov_start, start.normalize(), end.normalize())
                period_end = _bounded(cov_end, start.normalize(), end.normalize())
                if period_end < period_start:
                    continue
                amount = round(price, 2)
                invoice_rows.append({
                    "customer_id": cid,
                    "invoice_date": period_start.date(),  # issue at start of coverage
                    "amount": amount,
                    "is_refund": False,
                    "period_start": period_start.date(),
                    "period_end": period_end.date(),
                })

    invoices = pd.DataFrame(invoice_rows)

    # Optionally emit small refunds/credit memos
    n_refunds = int(len(invoices) * InvoicesConfig.refund_rate)
    if n_refunds > 0 and not invoices.empty:
        refund_indices = rng.choice(invoices.index, size=n_refunds, replace=False)
        refunds: List[dict] = []
        for idx in refund_indices:
            base_amount = float(invoices.loc[idx, "amount"])  # original
            pct = rng.uniform(*InvoicesConfig.refund_pct_of_invoice)
            credit = round(-base_amount * pct, 2)  # negative amount
            refunds.append({
                "customer_id": invoices.loc[idx, "customer_id"],
                "invoice_date": invoices.loc[idx, "invoice_date"],  # same month as original
                "amount": credit,
                "is_refund": True,
                "period_start": invoices.loc[idx, "period_start"],
                "period_end": invoices.loc[idx, "period_end"],
            })
        if refunds:
            invoices = pd.concat([invoices, pd.DataFrame(refunds)], ignore_index=True)

    # Sort and assign invoice_id
    invoices = invoices.sort_values(["customer_id", "invoice_date", "amount"]).reset_index(drop=True)
    invoices.insert(0, "invoice_id", [f"I{str(i).zfill(6)}" for i in range(1, len(invoices) + 1)])

    # Acceptance checks
    assert invoices["invoice_id"].is_unique, "invoice_id must be unique (PK)"
    valid_customers = set(customers["customer_id"].astype(str))
    assert set(invoices["customer_id"].astype(str)).issubset(valid_customers), "FK failure: customer_id unknown"
    assert (invoices["amount"] != 0).all(), "Invoices cannot have zero amount"
    assert invoices["invoice_date"].isna().sum() == 0, "invoice_date cannot be null"

    # Write/replace invoices sheet
    with pd.ExcelWriter(cfg.workbook_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        invoices.to_excel(writer, sheet_name=cfg.invoices_sheet, index=False)

    # Summary
    print("✅ invoices sheet generated/updated:")
    print(f"  -> rows: {len(invoices):,}")
    print("  -> refunds (rows):", int((invoices["is_refund"] == True).sum()))


if __name__ == "__main__":
    main()
