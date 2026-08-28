"""Reconciliation and control tests for the golden fixture."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.settings import BRIDGE_TOLERANCE, EXPECTED_ROW_COUNTS, OUTPUT_DIR


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


def _one(con, sql: str):
    return con.execute(sql).fetchone()


def _df(con, sql: str) -> pd.DataFrame:
    return con.execute(sql).df()


def run_validations(con) -> list[CheckResult]:
    results: list[CheckResult] = []

    for table, expected in EXPECTED_ROW_COUNTS.items():
        actual = _one(con, f"SELECT COUNT(*) FROM raw.{table}")[0]
        results.append(
            CheckResult(
                name=f"input_count_{table}",
                passed=actual == expected,
                detail=f"{table} rows={actual} expected={expected}",
            )
        )

    uniqueness = [
        ("customers", "customer_id"),
        ("subscriptions", "subscription_id"),
        ("events", "event_id"),
        ("invoices", "invoice_id"),
        ("payments", "payment_id"),
    ]
    for table, col in uniqueness:
        dup = _one(
            con,
            f"""
            SELECT COUNT(*) FROM (
                SELECT {col} FROM raw.{table} GROUP BY {col} HAVING COUNT(*) > 1
            )
            """,
        )[0]
        results.append(
            CheckResult(
                name=f"unique_{col}",
                passed=dup == 0,
                detail=f"{table}.{col} duplicate keys={dup}",
            )
        )

    fk_checks = [
        (
            "subscriptions_to_customers",
            """
            SELECT COUNT(*) FROM raw.subscriptions s
            ANTI JOIN raw.customers c USING (customer_id)
            """,
        ),
        (
            "events_to_customers",
            """
            SELECT COUNT(*) FROM raw.events e
            ANTI JOIN raw.customers c USING (customer_id)
            """,
        ),
        (
            "invoices_to_customers",
            """
            SELECT COUNT(*) FROM raw.invoices i
            ANTI JOIN raw.customers c USING (customer_id)
            """,
        ),
        (
            "payments_to_invoices",
            """
            SELECT COUNT(*) FROM raw.payments p
            ANTI JOIN raw.invoices i USING (invoice_id)
            """,
        ),
    ]
    for name, sql in fk_checks:
        orphans = _one(con, sql)[0]
        results.append(
            CheckResult(
                name=f"fk_{name}",
                passed=orphans == 0,
                detail=f"orphan rows={orphans}",
            )
        )

    na_count = _one(
        con,
        "SELECT COUNT(*) FROM raw.customers WHERE region = 'NA'",
    )[0]
    null_region = _one(
        con,
        "SELECT COUNT(*) FROM raw.customers WHERE region IS NULL OR region = ''",
    )[0]
    results.append(
        CheckResult(
            name="region_na_preserved",
            passed=na_count == 62 and null_region == 0,
            detail=f"region='NA' rows={na_count} expected=62; null/blank={null_region}",
        )
    )

    bridge_breaks = _one(
        con,
        f"""
        SELECT COUNT(*) FROM stg.mrr_bridge
        WHERE abs(end_mrr - implied_end_mrr) > {BRIDGE_TOLERANCE}
        """,
    )[0]
    max_gap = _one(
        con,
        "SELECT COALESCE(MAX(abs(end_mrr - implied_end_mrr)), 0) FROM stg.mrr_bridge",
    )[0]
    results.append(
        CheckResult(
            name="mrr_bridge_identity",
            passed=bridge_breaks == 0,
            detail=f"months_failing={bridge_breaks}; max_abs_gap={max_gap}",
        )
    )

    arr_bridge_breaks = _one(
        con,
        f"""
        SELECT COUNT(*) FROM stg.arr_revenue_bridge
        WHERE abs(end_arr - implied_end_arr) > {BRIDGE_TOLERANCE * 12}
        """,
    )[0]
    results.append(
        CheckResult(
            name="arr_bridge_identity",
            passed=arr_bridge_breaks == 0,
            detail=f"months_failing={arr_bridge_breaks}",
        )
    )

    arr_mismatch = _one(
        con,
        f"""
        SELECT COUNT(*)
        FROM stg.mrr m
        JOIN stg.arr a USING (month_start)
        WHERE abs(a.arr - m.mrr * 12) > {BRIDGE_TOLERANCE}
        """,
    )[0]
    results.append(
        CheckResult(
            name="arr_equals_mrr_times_12",
            passed=arr_mismatch == 0,
            detail=f"months_failing={arr_mismatch}",
        )
    )

    active_mismatch = _one(
        con,
        """
        SELECT COUNT(*)
        FROM stg.active_customers a
        JOIN (
            SELECT month_start, COUNT(DISTINCT customer_id) AS n
            FROM stg.mrr_extension
            GROUP BY month_start
        ) x USING (month_start)
        WHERE a.active_customers <> x.n
        """,
    )[0]
    results.append(
        CheckResult(
            name="active_customers_reconcile",
            passed=active_mismatch == 0,
            detail=f"months_failing={active_mismatch}",
        )
    )

    grr_oob = _one(
        con,
        """
        SELECT COUNT(*) FROM stg.nrr_grr
        WHERE beg_mrr > 0
          AND (grr IS NULL OR grr < 0 OR grr > 1.0000001)
        """,
    )[0]
    results.append(
        CheckResult(
            name="grr_between_0_and_1",
            passed=grr_oob == 0,
            detail=f"months_outside_0_1={grr_oob}",
        )
    )

    nrr_unexplainable = _one(
        con,
        """
        SELECT COUNT(*) FROM stg.nrr_grr
        WHERE beg_mrr > 0 AND (nrr IS NULL OR nrr < 0)
        """,
    )[0]
    results.append(
        CheckResult(
            name="nrr_non_negative_when_beg_positive",
            passed=nrr_unexplainable == 0,
            detail=f"months_failing={nrr_unexplainable}",
        )
    )

    kpi_neg = _one(
        con,
        """
        SELECT COUNT(*) FROM stg.kpi
        WHERE mrr < 0
           OR arpu < 0
           OR payback_months < 0
        """,
    )[0]
    results.append(
        CheckResult(
            name="kpi_non_negative_values",
            passed=kpi_neg == 0,
            detail=f"rows_with_negative_mrr_arpu_or_payback={kpi_neg}",
        )
    )

    return results


def write_outputs(con, output_dir: Path | None = None) -> list[Path]:
    directory = Path(output_dir) if output_dir is not None else OUTPUT_DIR
    directory.mkdir(parents=True, exist_ok=True)

    exports = {
        "kpi_monthly.csv": """
            SELECT * FROM stg.kpi ORDER BY month_start
        """,
        "mrr_bridge.csv": """
            SELECT
                b.month_start,
                b.beg_mrr,
                b.new_mrr,
                b.expansion_mrr,
                b.reactivation_mrr,
                b.contraction_mrr,
                b.churn_mrr,
                b.end_mrr,
                b.implied_end_mrr,
                (b.end_mrr - b.implied_end_mrr) AS bridge_gap,
                ab.beg_arr,
                ab.new_arr,
                ab.expansion_arr,
                ab.reactivation_arr,
                ab.contraction_arr,
                ab.churn_arr,
                ab.end_arr
            FROM stg.mrr_bridge b
            JOIN stg.arr_revenue_bridge ab USING (month_start)
            ORDER BY b.month_start
        """,
        "cohort_retention.csv": """
            SELECT * FROM stg.retention_cohorts
            ORDER BY cohort_month, months_since_signup
        """,
        "channel_metrics.csv": """
            SELECT * FROM stg.channel_kpi
            ORDER BY month_start, acquisition_channel
        """,
        "segment_metrics.csv": """
            SELECT * FROM stg.segment_kpi
            ORDER BY month_start, segment
        """,
        "unit_economics.csv": """
            SELECT
                month_start,
                new_customers,
                cac_total,
                cac_per_customer,
                arpu,
                active_customers,
                gross_margin,
                revenue_churn_rate,
                payback_months,
                modeled_ltv_revenue_churn
            FROM stg.cac_ltv
            ORDER BY month_start
        """,
        "assumptions.csv": """
            SELECT * FROM stg.assumptions
        """,
    }

    written: list[Path] = []
    for filename, sql in exports.items():
        path = directory / filename
        _df(con, sql).to_csv(path, index=False)
        written.append(path)
    return written


def write_validation_summary(
    results: list[CheckResult], output_dir: Path | None = None
) -> Path:
    directory = Path(output_dir) if output_dir is not None else OUTPUT_DIR
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "validation_summary.csv"
    pd.DataFrame(
        [
            {
                "check": r.name,
                "passed": r.passed,
                "detail": r.detail,
            }
            for r in results
        ]
    ).to_csv(path, index=False)
    return path
