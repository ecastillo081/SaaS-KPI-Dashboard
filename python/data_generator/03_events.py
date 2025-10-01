"""
Generate or update the `events` sheet in saas_kpi_seeds.xlsx (Phase 1 / Table 3).

This derives lifecycle events from `subscriptions` so NRR/GRR and ARR bridge components
(expansion, contraction, churn, new logo, reactivation) can be computed cleanly.

Event types emitted per customer (in chronological order):
- new           : first subscription start (+delta_mrr = starting price_mrr)
- upgrade       : next period starts with higher price_mrr (+delta_mrr)
- downgrade     : next period starts with lower price_mrr ( -delta_mrr )
- churn         : a period ends (end_date not NULL) ( -delta_mrr = current price_mrr )
- reactivation  : a new period begins after a churn gap (+delta_mrr = new price_mrr)

Schema:
- event_id (PK)         : string like E000001
- customer_id (FK)      : customers.customer_id
- event_date            : date of the change (start_date for new/reactivation/upgrade/downgrade; end_date for churn)
- event_type            : one of [new, upgrade, downgrade, churn, reactivation]
- plan_from             : plan before the change (None for `new`)
- plan_to               : plan after the change (None for `churn`)
- delta_mrr             : signed change to MRR due to the event (positive for new/upgrade/reactivation; negative for downgrade/churn)

Run: `python 03_generate_events.py`
Requires: pandas, numpy, openpyxl
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd


@dataclass
class EventsConfig:
    workbook_path: str = "saas_kpi_seeds.xlsx"
    customers_sheet: str = "customers"
    subs_sheet: str = "subscriptions"
    events_sheet: str = "events"
    random_seed: int = 321


def _append_event(events: List[dict], cid: str, dt: pd.Timestamp, etype: str,
                  plan_from: Optional[str], plan_to: Optional[str], delta: float) -> None:
    events.append({
        "customer_id": cid,
        "event_date": dt.date(),
        "event_type": etype,
        "plan_from": plan_from,
        "plan_to": plan_to,
        "delta_mrr": round(float(delta), 2),
    })


def _build_events_for_customer(subs_cust: pd.DataFrame) -> List[dict]:
    """Emit events from ordered subscription periods for one customer."""
    out: List[dict] = []
    # Ensure ordering
    s = subs_cust.sort_values(["start_date"]).reset_index(drop=True).copy()

    if s.empty:
        return out

    # First period => `new`
    first = s.iloc[0]
    _append_event(out, first.customer_id, pd.to_datetime(first.start_date),
                  "new", None, first.plan, float(first.price_mrr))

    # If first period later ends => `churn`
    if pd.notna(first.end_date):
        _append_event(out, first.customer_id, pd.to_datetime(first.end_date),
                      "churn", first.plan, None, -float(first.price_mrr))

    # Subsequent periods
    for i in range(1, len(s)):
        prev = s.iloc[i-1]
        cur = s.iloc[i]

        # Reactivation vs upgrade/downgrade
        # If previous ended before current starts, we consider a reactivation (gap > 0 days)
        prev_end = pd.to_datetime(prev.end_date) if pd.notna(prev.end_date) else None
        cur_start = pd.to_datetime(cur.start_date)

        if prev_end is not None and cur_start > prev_end:
            # Reactivation at cur_start (positive delta = cur.price_mrr)
            _append_event(out, cur.customer_id, cur_start, "reactivation",
                          None, cur.plan, float(cur.price_mrr))
        else:
            # Continuous service: treat change at cur_start as upgrade/downgrade if price differs
            delta = float(cur.price_mrr) - float(prev.price_mrr)
            if delta > 0.0:
                _append_event(out, cur.customer_id, cur_start, "upgrade",
                              prev.plan, cur.plan, delta)
            elif delta < 0.0:
                _append_event(out, cur.customer_id, cur_start, "downgrade",
                              prev.plan, cur.plan, delta)  # negative
            else:
                # same price_mrr and likely same plan — no event
                pass

        # Churn for current period if it ends
        if pd.notna(cur.end_date):
            _append_event(out, cur.customer_id, pd.to_datetime(cur.end_date),
                          "churn", cur.plan, None, -float(cur.price_mrr))

    return out


def main():
    cfg = EventsConfig()

    if not os.path.exists(cfg.workbook_path):
        raise FileNotFoundError(
            f"Workbook '{cfg.workbook_path}' not found. Run previous generators first."
        )

    customers = pd.read_excel(cfg.workbook_path, sheet_name=cfg.customers_sheet, engine="openpyxl")
    subs = pd.read_excel(cfg.workbook_path, sheet_name=cfg.subs_sheet, engine="openpyxl")
    if customers.empty or subs.empty:
        raise ValueError("Required sheets missing or empty.")

    # Basic FK check set
    valid_customers = set(customers["customer_id"].astype(str))

    # Ensure date types
    for col in ("start_date", "end_date"):
        if col in subs.columns:
            subs[col] = pd.to_datetime(subs[col])

    # Build events across all customers
    all_events: List[dict] = []
    for cid, group in subs.groupby("customer_id", as_index=False):
        cust_events = _build_events_for_customer(group)
        all_events.extend(cust_events)

    events = pd.DataFrame(all_events)

    # Assign event_id and sort
    events = events.sort_values(["customer_id", "event_date"]).reset_index(drop=True)
    events.insert(0, "event_id", [f"E{str(i).zfill(6)}" for i in range(1, len(events) + 1)])

    # Acceptance checks
    assert events["event_id"].is_unique, "event_id must be unique (PK)"
    assert set(events["customer_id"].astype(str)).issubset(valid_customers), "FK failure: customer_id unknown"
    assert events["event_date"].isna().sum() == 0, "event_date cannot be null"

    # Chronology check: events per customer strictly increasing by date
    def _check_monotonic(g: pd.DataFrame):
        if not g["event_date"].is_monotonic_increasing:
            raise AssertionError(f"Events not in chronological order for customer {g['customer_id'].iloc[0]}")
    events.groupby("customer_id", as_index=False).apply(_check_monotonic)

    # Rolling MRR sanity: start at 0, apply deltas, never negative
    def _rolling_ok(g: pd.DataFrame):
        mrr = 0.0
        for _, r in g.iterrows():
            mrr += float(r["delta_mrr"])  # signed
            if mrr < -1e-6:
                raise AssertionError(f"Rolling MRR went negative for {g['customer_id'].iloc[0]}")
    events.groupby("customer_id", as_index=False).apply(_rolling_ok)

    # Write/replace events sheet
    with pd.ExcelWriter(cfg.workbook_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        events.to_excel(writer, sheet_name=cfg.events_sheet, index=False)

    # Summary
    print("✅ events sheet generated/updated:")
    print(f"  -> rows: {len(events):,}")
    print(events["event_type"].value_counts().to_string())


if __name__ == "__main__":
    main()
