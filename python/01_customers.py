"""
Generate an Excel workbook with a `customers` sheet for a SaaS KPI portfolio project.

What this script does (Phase 1 / Table 1):
- Creates or updates an Excel file `saas_kpi_data.xlsx`.
- Writes a `customers` sheet with 100 rows by default (tunable).
- Enforces clean primary keys and realistic business rules.
- Provides deterministic synthesis via a random seed.
- Replaces only the `customers` sheet if the workbook already exists (safe for future sheets).

Columns (schema):
- customer_id (PK)           : string like C0001, C0002, ...
- signup_date                : date the logo converted
- segment                    : one of [SMB, Mid, Enterprise]
- region                     : one of [NA, EMEA, APAC, LATAM]
- acquisition_channel        : one of [Paid, Organic, Partner, Outbound]
- cac                        : numeric (no currency suffix in the column name)

Usage:
- Run directly: `python 01_generate_customers.py`
- Adjust knobs in CONFIG below.

Requires:
- pandas >= 1.4 (for if_sheet_exists="replace")
- openpyxl (Excel engine)

This script is idempotent for the `customers` sheet: re-running will replace that sheet only.
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List

import numpy as np
import pandas as pd

# ============================
# -------- CONFIG  -----------
# ============================
@dataclass
class CustomersConfig:
    output_path: str = "../data/saas_kpi_data.xlsx"  # Excel workbook name
    sheet_name: str = "customers"
    random_seed: int = 42

    # Scale knobs
    num_customers: int = 100

    # Time window for realistic signup dates
    # Example: last 18 months through the end of last month
    months_back: int = 18

    # Mixes / distributions
    segment_mix: Dict[str, float] = None
    region_mix: Dict[str, float] = None
    channel_mix: Dict[str, float] = None

    # CAC ranges by channel (min, max) in same units as your data (no suffix)
    cac_ranges_by_channel: Dict[str, tuple] = None

    def __post_init__(self):
        if self.segment_mix is None:
            self.segment_mix = {"SMB": 0.65, "Mid": 0.28, "Enterprise": 0.07}
        if self.region_mix is None:
            self.region_mix = {"NA": 0.60, "EMEA": 0.20, "APAC": 0.15, "LATAM": 0.05}
        if self.channel_mix is None:
            self.channel_mix = {"Paid": 0.45, "Organic": 0.25, "Partner": 0.20, "Outbound": 0.10}
        if self.cac_ranges_by_channel is None:
            # Tweak as desired; Paid typically higher CAC, Organic lower.
            self.cac_ranges_by_channel = {
                "Paid": (700, 1200),
                "Partner": (500, 900),
                "Outbound": (300, 800),
                "Organic": (50, 400),
            }


def _choice_with_mix(rng: np.random.Generator, mix: Dict[str, float], size: int) -> List[str]:
    labels = list(mix.keys())
    probs = np.array(list(mix.values()), dtype=float)
    # Normalize to guard against minor rounding issues
    probs = probs / probs.sum()
    return rng.choice(labels, size=size, p=probs)


def _generate_signup_dates(rng: np.random.Generator, n: int, months_back: int) -> List[date]:
    """Spread signups across the last `months_back` months with a slight recent bias."""
    # End at the end of last month to avoid partial current month effects
    today = pd.Timestamp.today().normalize()
    end_month = (today.replace(day=1) - pd.offsets.Day(1))  # last day of previous month
    start_month = (end_month - pd.DateOffset(months=months_back-1)).replace(day=1)

    all_days = pd.date_range(start_month, end_month, freq="D")

    # Bias toward more recent days (linear ramp)
    weights = np.linspace(0.6, 1.0, num=len(all_days))
    weights = weights / weights.sum()

    chosen = rng.choice(all_days, size=n, p=weights)
    return pd.to_datetime(chosen).date.tolist()


def generate_customers_df(cfg: CustomersConfig) -> pd.DataFrame:
    rng = np.random.default_rng(cfg.random_seed)

    # Primary keys: C0001..CXXXX
    customer_ids = [f"C{str(i).zfill(4)}" for i in range(1, cfg.num_customers + 1)]

    signup_dates = _generate_signup_dates(rng, cfg.num_customers, cfg.months_back)
    segments = _choice_with_mix(rng, cfg.segment_mix, cfg.num_customers)
    regions = _choice_with_mix(rng, cfg.region_mix, cfg.num_customers)
    channels = _choice_with_mix(rng, cfg.channel_mix, cfg.num_customers)

    # CAC sampled uniformly within channel-specific ranges
    cac_values = []
    for ch in channels:
        low, high = cfg.cac_ranges_by_channel[ch]
        cac_values.append(rng.uniform(low, high))

    df = pd.DataFrame(
        {
            "customer_id": customer_ids,
            "signup_date": pd.to_datetime(signup_dates).date,
            "segment": segments,
            "region": regions,
            "acquisition_channel": channels,
            "cac": np.round(cac_values, 2),  # round to cents (or leave as integer if preferred)
        }
    )

    # Acceptance checks
    assert df.shape[0] == cfg.num_customers, "Row count mismatch vs num_customers"
    assert df["customer_id"].is_unique, "customer_id must be unique (PK)"
    assert df.isna().sum().sum() == 0, "No nulls allowed in customers table"

    # signup_date sanity (not in the future)
    assert df["signup_date"].max() <= pd.Timestamp.today().date(), "signup_date cannot be in the future"

    return df


def write_or_update_sheet(df: pd.DataFrame, path: str, sheet_name: str) -> None:
    """Create or update an Excel workbook. Replace only the target sheet if file exists."""
    if os.path.exists(path):
        # Update (replace) sheet only
        with pd.ExcelWriter(path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    else:
        # Create new workbook
        with pd.ExcelWriter(path, engine="openpyxl", mode="w") as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)


def main():
    cfg = CustomersConfig()
    df = generate_customers_df(cfg)
    write_or_update_sheet(df, cfg.output_path, cfg.sheet_name)

    # Simple summary for the console
    seg_counts = df["segment"].value_counts().to_dict()
    reg_counts = df["region"].value_counts().to_dict()
    ch_counts = df["acquisition_channel"].value_counts().to_dict()

    print("✅ customers sheet generated/updated:")
    print(f"  -> rows: {len(df):,}")
    print(f"  -> segments: {seg_counts}")
    print(f"  -> regions:  {reg_counts}")
    print(f"  -> channels: {ch_counts}")
    print(f"  -> output:   {os.path.abspath(cfg.output_path)}")


if __name__ == "__main__":
    main()
