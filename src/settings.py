"""Shared Phase 1 build settings. Paths are repo-relative."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_AS_OF_DATE = "2025-09-30"
WORKBOOK_PATH = REPO_ROOT / "data" / "saas_kpi_data.xlsx"
SQL_DIR = REPO_ROOT / "sql"
WAREHOUSE_DIR = REPO_ROOT / "warehouse"
DUCKDB_PATH = WAREHOUSE_DIR / "saas_kpi.duckdb"
OUTPUT_DIR = REPO_ROOT / "outputs"

GROSS_MARGIN = "0.80"

EXPECTED_ROW_COUNTS = {
    "customers": 100,
    "subscriptions": 114,
    "events": 180,
    "invoices": 779,
    "payments": 636,
}

BRIDGE_TOLERANCE = 0.01
