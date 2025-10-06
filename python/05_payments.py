"""
Generate or update the `payments` sheet in saas_kpi_data.xlsx (Phase 1 / Table 5).

Design:
- Reads `invoices` to emit cash receipts applied to each invoice (AR → cash).
- Configurable mix of fully-paid, partial-paid, and unpaid invoices.
- Realistic payment lags (same-day to Net-30/45), never future-dated.
- Credit memos / refunds (negative invoices): mostly non-cash offsets; a small percent generate
  true cash refunds (negative payments).

Schema:
- payment_id (PK)    : string like P000001
- invoice_id (FK)    : invoices.invoice_id
- payment_date       : date cash was received (or refunded)
- amount             : positive for customer payments; negative for cash refunds
- payment_method     : enum [ACH, Card, Wire, Check]

Run: `python 05_generate_payments.py`
Requires: pandas, numpy, openpyxl
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd


@dataclass
class PaymentsConfig:
    workbook_path: str = "../data/saas_kpi_data.xlsx"
    invoices_sheet: str = "invoices"
    payments_sheet: str = "payments"
    random_seed: int = 789

    # Mix of payment outcomes for positive invoices
    pct_fully_paid: float = 0.85
    pct_partial_paid: float = 0.00
    pct_unpaid: float = 0.15

    # For partial payments, how many parts (2 or 3)
    partial_parts_probs = {2: 0.75, 3: 0.25}

    # Payment lag windows (days)
    lag_min_days: int = 30
    lag_max_days: int = 30

    # Payment methods distribution
    method_probs = {"ACH": 0.55, "Card": 0.20, "Wire": 0.15, "Check": 0.10}

    # Credit memos / refunds (negative invoices)
    pct_cash_refund_for_credit_memos: float = 0.00  # 0% trigger actual cash refund (negative payment)


def _choice_with_mix(rng: np.random.Generator, mix: dict) -> str:
    labels = list(mix.keys())
    probs = np.array(list(mix.values()), dtype=float)
    probs = probs / probs.sum()
    return rng.choice(labels, p=probs)


def _emit_payments_for_positive_invoice(rng: np.random.Generator, inv: pd.Series, cfg: PaymentsConfig) -> List[dict]:
    out: List[dict] = []
    amt = float(inv["amount"])  # positive

    r = rng.random()
    if r < cfg.pct_fully_paid:
        # Single full payment
        parts = [amt]
    elif r < cfg.pct_fully_paid + cfg.pct_partial_paid:
        # Partial into 2–3 payments
        parts_n = _choice_with_mix(rng, cfg.partial_parts_probs)
        # Random split that sums to amt
        weights = rng.random(parts_n)
        weights = weights / weights.sum()
        parts = [round(amt * w, 2) for w in weights]
        # Fix rounding drift on last part
        drift = round(amt - sum(parts), 2)
        parts[-1] = round(parts[-1] + drift, 2)
    else:
        # Unpaid
        parts = []

    for p_amt in parts:
        lag_days = int(rng.integers(cfg.lag_min_days, cfg.lag_max_days + 1))
        pay_date = pd.Timestamp(inv["invoice_date"]) + pd.Timedelta(days=lag_days)
        pay_date = min(pay_date.normalize(), pd.Timestamp.today().normalize())  # no future dates
        out.append({
            "invoice_id": inv["invoice_id"],
            "payment_date": pay_date.date(),
            "amount": round(p_amt, 2),
            "payment_method": _choice_with_mix(rng, cfg.method_probs),
        })
    return out


def _emit_payments_for_negative_invoice(rng: np.random.Generator, inv: pd.Series, cfg: PaymentsConfig) -> List[dict]:
    out: List[dict] = []
    amt = float(inv["amount"])  # negative (credit memo)

    # Most credit memos are non-cash; occasionally issue a cash refund (negative payment)
    if rng.random() < cfg.pct_cash_refund_for_credit_memos:
        lag_days = int(rng.integers(cfg.lag_min_days, cfg.lag_max_days + 1))
        pay_date = pd.Timestamp(inv["invoice_date"]) + pd.Timedelta(days=lag_days)
        pay_date = min(pay_date.normalize(), pd.Timestamp.today().normalize())
        out.append({
            "invoice_id": inv["invoice_id"],
            "payment_date": pay_date.date(),
            "amount": round(amt, 2),  # negative cash flow
            "payment_method": _choice_with_mix(rng, cfg.method_probs),
        })
    # else: no cash movement (AR offset only)
    return out


def main():
    cfg = PaymentsConfig()

    if not os.path.exists(cfg.workbook_path):
        raise FileNotFoundError(f"Workbook '{cfg.workbook_path}' not found. Generate invoices first.")

    invoices = pd.read_excel(cfg.workbook_path, sheet_name=cfg.invoices_sheet, engine="openpyxl")
    if invoices.empty:
        raise ValueError("Invoices sheet is empty; cannot create payments.")

    rng = np.random.default_rng(cfg.random_seed)

    # Split positive vs negative invoices
    pos_inv = invoices[invoices["amount"] > 0].copy()
    neg_inv = invoices[invoices["amount"] < 0].copy()

    payment_rows: List[dict] = []

    for _, inv in pos_inv.iterrows():
        payment_rows.extend(_emit_payments_for_positive_invoice(rng, inv, cfg))

    for _, inv in neg_inv.iterrows():
        payment_rows.extend(_emit_payments_for_negative_invoice(rng, inv, cfg))

    payments = pd.DataFrame(payment_rows)

    # Assign payment_id and sort
    payments = payments.sort_values(["invoice_id", "payment_date"]).reset_index(drop=True)
    payments.insert(0, "payment_id", [f"P{str(i).zfill(6)}" for i in range(1, len(payments) + 1)])

    # Acceptance checks
    assert payments["payment_id"].is_unique, "payment_id must be unique (PK)"
    valid_invoices = set(invoices["invoice_id"].astype(str))
    assert set(payments["invoice_id"].astype(str)).issubset(valid_invoices), "FK failure: unknown invoice_id"
    assert payments["payment_date"].isna().sum() == 0, "payment_date cannot be null"

    # Sanity: no future-dated payments
    assert payments["payment_date"].max() <= pd.Timestamp.today().date(), "payment_date cannot be in the future"

    # Optional reconciliation check (soft): ensure sum of payments <= invoice amount for positive invoices
    merged = payments.merge(invoices[["invoice_id", "amount"]], on="invoice_id", how="left", suffixes=("_p", "_i"))
    by_inv = merged.groupby("invoice_id", as_index=False).agg(paid_sum=("amount_p", "sum"), inv_amt=("amount_i", "first"))
    overpays = by_inv[(by_inv["inv_amt"] > 0) & (by_inv["paid_sum"] > by_inv["inv_amt"] + 0.01)]
    assert overpays.empty, "Some positive invoices are overpaid; check generation logic."

    # Write/replace payments sheet
    with pd.ExcelWriter(cfg.workbook_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        payments.to_excel(writer, sheet_name=cfg.payments_sheet, index=False)

    # Summary
    print("✅ payments sheet generated/updated:")
    print(f"  -> rows: {len(payments):,}")
    print("  -> sample methods:")
    print(payments["payment_method"].value_counts().head(4).to_string())


if __name__ == "__main__":
    main()
