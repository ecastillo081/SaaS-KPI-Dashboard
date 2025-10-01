"""
Generate or update the `subscriptions` sheet in saas_kpi_seeds.xlsx (Phase 1 / Table 2).

What this script does:
- Reads `customers` from the workbook to enforce FK integrity.
- Creates 1–2 subscription periods per customer to allow churn/reactivation scenarios.
- Assigns plans based on customer segment with realistic base MRRs (+ small noise).
- Ensures date/business rules: start_date >= signup_date, no overlaps per customer,
  end_date is NULL for active rows, otherwise status='canceled'.
- Replaces only the `subscriptions` sheet if the workbook already exists.

Schema:
- subscription_id (PK)   : string like S000001
- customer_id (FK)       : must exist in customers.customer_id
- start_date             : date subscription period starts (>= signup_date)
- end_date               : date subscription period ends (NULL for active)
- plan                   : tier name (Starter, Pro, Business, Enterprise)
- price_mrr              : numeric monthly recurring revenue for this period
- status                 : 'active' if end_date is NULL else 'canceled'

Run: `python 02_generate_subscriptions.py`
Requires: pandas, numpy, openpyxl
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


# ============================
# -------- CONFIG  -----------
# ============================
@dataclass
class SubsConfig:
    workbook_path: str = "../data/saas_kpi_seeds.xlsx"
    customers_sheet: str = "customers"
    subs_sheet: str = "subscriptions"
    random_seed: int = 123

    # Controls
    max_periods_per_customer: int = 2          # enables churn/reactivation
    pct_reactivate: float = 0.20               # chance a churned customer returns for a 2nd period

    # Month ranges for period durations (in months)
    min_months: int = 3
    max_months: int = 18

    # Buffer (days) between signup and first start_date (simulates provisioning delay)
    start_delay_days_min: int = 0
    start_delay_days_max: int = 10

    # Gap between periods if reactivated (days)
    reactivation_gap_min: int = 15
    reactivation_gap_max: int = 60

    # Plan catalog with base MRRs (can be tuned)
    plan_prices: Dict[str, Tuple[int, int]] = None  # (base_low, base_high)

    # Segment → plan distribution
    segment_plan_mix: Dict[str, Dict[str, float]] = None

    # Noise applied to base MRR (+/- up to percentage)
    price_noise_pct: float = 0.00  # up to 8% noise

    def __post_init__(self):
        if self.plan_prices is None:
            self.plan_prices = {
                "Starter":   (20, 20), # these are bands
                "Pro":       (50, 50),
                "Business":  (150, 150),
                "Enterprise":(500, 500),
            }
        if self.segment_plan_mix is None:
            self.segment_plan_mix = {
                "SMB": {"Starter": 0.55, "Pro": 0.40, "Business": 0.05, "Enterprise": 0.00},
                "Mid": {"Starter": 0.10, "Pro": 0.55, "Business": 0.30, "Enterprise": 0.05},
                "Enterprise": {"Starter": 0.00, "Pro": 0.15, "Business": 0.45, "Enterprise": 0.40},
            }


def _choice_with_mix(rng: np.random.Generator, mix: Dict[str, float]) -> str:
    labels = list(mix.keys())
    probs = np.array(list(mix.values()), dtype=float)
    probs = probs / probs.sum()
    return rng.choice(labels, p=probs)


def _sample_price_mrr(rng: np.random.Generator, plan: str, cfg: SubsConfig) -> float:
    low, high = cfg.plan_prices[plan]
    base = rng.uniform(low, high)
    noise = base * rng.uniform(-cfg.price_noise_pct, cfg.price_noise_pct)
    return round(max(5.0, base + noise), 2)


def _gen_periods_for_customer(rng: np.random.Generator, row: pd.Series, cfg: SubsConfig) -> List[dict]:
    periods: List[dict] = []

    signup_date = pd.to_datetime(row["signup_date"]).date()
    segment = row["segment"]

    # First period
    start_delay_days = rng.integers(cfg.start_delay_days_min, cfg.start_delay_days_max + 1)
    start_1 = pd.Timestamp(signup_date) + pd.Timedelta(days=int(start_delay_days))
    months_1 = int(rng.integers(cfg.min_months, cfg.max_months + 1))
    end_1 = (start_1 + pd.DateOffset(months=months_1)) - pd.Timedelta(days=1)

    plan_1 = _choice_with_mix(rng, cfg.segment_plan_mix.get(segment, cfg.segment_plan_mix["SMB"]))
    price_1 = _sample_price_mrr(rng, plan_1, cfg)

    # Determine if still active (50/50) with a slight skew to active for longer recent cohorts
    today = pd.Timestamp.today().normalize()
    active_bias = 0.55
    still_active = rng.random() < active_bias and end_1 > today

    end_date_1 = None if still_active else end_1.date()
    status_1 = "active" if end_date_1 is None else "canceled"

    periods.append({
        "customer_id": row["customer_id"],
        "start_date": start_1.date(),
        "end_date": end_date_1,  # NULL if active
        "plan": plan_1,
        "price_mrr": price_1,
        "status": status_1,
    })

    # Optional reactivation period
    wants_second = (not still_active) and (rng.random() < cfg.pct_reactivate)
    if wants_second:
        gap_days = int(rng.integers(cfg.reactivation_gap_min, cfg.reactivation_gap_max + 1))
        start_2 = end_1 + pd.Timedelta(days=gap_days)
        months_2 = int(rng.integers(cfg.min_months, cfg.max_months + 1))
        end_2 = (start_2 + pd.DateOffset(months=months_2)) - pd.Timedelta(days=1)

        # Often reactivations shift plan up or down
        plan_2 = _choice_with_mix(rng, cfg.segment_plan_mix.get(segment, cfg.segment_plan_mix["SMB"]))
        price_2 = _sample_price_mrr(rng, plan_2, cfg)

        still_active_2 = rng.random() < 0.65 and end_2 > today
        end_date_2 = None if still_active_2 else end_2.date()
        status_2 = "active" if end_date_2 is None else "canceled"

        periods.append({
            "customer_id": row["customer_id"],
            "start_date": start_2.date(),
            "end_date": end_date_2,
            "plan": plan_2,
            "price_mrr": price_2,
            "status": status_2,
        })

    return periods


def _validate_no_overlap(df: pd.DataFrame) -> None:
    # For each customer, ensure no overlapping periods
    def _check(group: pd.DataFrame):
        g = group.sort_values("start_date").copy()
        prev_end = None
        for _, r in g.iterrows():
            s = pd.to_datetime(r["start_date"]).date()
            e = r["end_date"]
            if pd.notna(e):
                e = pd.to_datetime(e).date()
            if prev_end is not None and s <= prev_end:
                raise AssertionError(f"Overlapping periods for customer {r['customer_id']}")
            prev_end = e if e is not None else prev_end
    df.groupby("customer_id", as_index=False).apply(_check)


def main():
    cfg = SubsConfig()

    if not os.path.exists(cfg.workbook_path):
        raise FileNotFoundError(
            f"Workbook '{cfg.workbook_path}' not found. Run 01_generate_customers.py first."
        )

    # Read customers sheet
    customers = pd.read_excel(cfg.workbook_path, sheet_name=cfg.customers_sheet, engine="openpyxl")
    if customers.empty:
        raise ValueError("Customers sheet is empty; cannot create subscriptions.")

    rng = np.random.default_rng(cfg.random_seed)

    # Build periods list
    all_periods: List[dict] = []
    for _, row in customers.iterrows():
        periods = _gen_periods_for_customer(rng, row, cfg)
        all_periods.extend(periods)

    subs = pd.DataFrame(all_periods)

    # Sort by customer and start_date for stable IDs
    subs = subs.sort_values(["customer_id", "start_date"]).reset_index(drop=True)

    # Assign subscription_id
    subs.insert(0, "subscription_id", [f"S{str(i).zfill(6)}" for i in range(1, len(subs) + 1)])

    # Acceptance checks
    assert subs["subscription_id"].is_unique, "subscription_id must be unique (PK)"
    # FK integrity
    valid_customers = set(customers["customer_id"].astype(str))
    assert set(subs["customer_id"].astype(str)).issubset(valid_customers), "FK failure: unknown customer_id"

    # Date sanity
    # start_date >= signup_date
    merged = subs.merge(customers[["customer_id", "signup_date"]], on="customer_id", how="left")
    assert (pd.to_datetime(merged["start_date"]).dt.date >= pd.to_datetime(merged["signup_date"]).dt.date).all(), \
        "start_date must be >= signup_date"

    # end_date is either NULL or > start_date
    with_end = subs[pd.notna(subs["end_date"])]
    assert (pd.to_datetime(with_end["end_date"]).dt.date > pd.to_datetime(with_end["start_date"]).dt.date).all(), \
        "end_date must be > start_date when present"

    # No overlaps per customer
    _validate_no_overlap(subs)

    # Write/replace subscriptions sheet
    with pd.ExcelWriter(cfg.workbook_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        subs.to_excel(writer, sheet_name=cfg.subs_sheet, index=False)

    # Summary
    print("✅ subscriptions sheet generated/updated:")
    print(f"  -> rows: {len(subs):,}")
    print("  -> active rows:", (subs["status"] == "active").sum())
    print("  -> canceled rows:", (subs["status"] == "canceled").sum())
    print("  -> plans:")
    print(subs["plan"].value_counts().to_string())


if __name__ == "__main__":
    main()
