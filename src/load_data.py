"""Load the golden Excel fixture into DuckDB schema `raw`."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.settings import EXPECTED_ROW_COUNTS, WORKBOOK_PATH

SHEETS = ("customers", "subscriptions", "events", "invoices", "payments")

DATE_COLUMNS = {
    "customers": ("signup_date",),
    "subscriptions": ("start_date", "end_date"),
    "events": ("event_date",),
    "invoices": ("invoice_date", "period_start", "period_end"),
    "payments": ("payment_date",),
}


def _read_sheet(workbook_path: Path, sheet_name: str) -> pd.DataFrame:
    # keep_default_na=False preserves region value "NA" (North America).
    df = pd.read_excel(
        workbook_path,
        sheet_name=sheet_name,
        engine="openpyxl",
        keep_default_na=False,
    )
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    for col in DATE_COLUMNS.get(sheet_name, ()):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    if sheet_name == "customers" and "region" in df.columns:
        df["region"] = df["region"].astype(str)

    if sheet_name == "invoices" and "is_refund" in df.columns:
        df["is_refund"] = df["is_refund"].astype(bool)

    return df


def load_workbook(con, workbook_path: Path | None = None) -> dict[str, int]:
    path = Path(workbook_path) if workbook_path is not None else WORKBOOK_PATH
    if not path.exists():
        raise FileNotFoundError(f"Golden workbook not found: {path}")

    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    row_counts: dict[str, int] = {}

    for sheet_name in SHEETS:
        df = _read_sheet(path, sheet_name)
        row_counts[sheet_name] = len(df)
        expected = EXPECTED_ROW_COUNTS[sheet_name]
        if len(df) != expected:
            raise ValueError(
                f"Sheet '{sheet_name}' has {len(df)} rows; golden fixture expects {expected}. "
                "The workbook was not rewritten; check that data/saas_kpi_data.xlsx is unchanged."
            )

        tmp_name = f"_load_{sheet_name}"
        con.register(tmp_name, df)
        con.execute(f"DROP TABLE IF EXISTS raw.{sheet_name}")
        con.execute(f"CREATE TABLE raw.{sheet_name} AS SELECT * FROM {tmp_name}")
        con.unregister(tmp_name)

        date_cols = DATE_COLUMNS.get(sheet_name, ())
        if date_cols:
            casts = ", ".join(
                f"{col}::DATE AS {col}" if col in date_cols else col
                for col in df.columns
            )
            con.execute(
                f"CREATE OR REPLACE TABLE raw.{sheet_name} AS SELECT {casts} FROM raw.{sheet_name}"
            )

    return row_counts
