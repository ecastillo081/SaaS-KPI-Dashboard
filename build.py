"""Local DuckDB build: load golden workbook, apply SQL, validate, export CSVs."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

import duckdb

from src.settings import (
    DEFAULT_AS_OF_DATE,
    DUCKDB_PATH,
    OUTPUT_DIR,
    WAREHOUSE_DIR,
    WORKBOOK_PATH,
)
from src.build_models import build_models
from src.load_data import load_workbook
from src.validate import run_validations, write_outputs, write_validation_summary


def _parse_as_of(value: str) -> str:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError("as-of must be YYYY-MM-DD") from exc
    return parsed.isoformat()


def _print_metric_summary(con) -> None:
    row = con.execute(
        """
        SELECT
            (SELECT min(month_start) FROM stg.date_spine) AS start_month,
            (SELECT max(month_start) FROM stg.date_spine) AS end_month,
            (SELECT as_of_date FROM stg.assumptions) AS as_of_date,
            (SELECT mrr FROM stg.mrr ORDER BY month_start DESC LIMIT 1) AS ending_mrr,
            (SELECT arr FROM stg.arr ORDER BY month_start DESC LIMIT 1) AS ending_arr,
            (SELECT max(arr) FROM stg.arr) AS peak_arr,
            (
                SELECT month_start FROM stg.arr
                WHERE arr = (SELECT max(arr) FROM stg.arr)
                ORDER BY month_start
                LIMIT 1
            ) AS peak_arr_month,
            (SELECT avg(nrr) FROM stg.nrr_grr WHERE beg_mrr > 0) AS mean_nrr,
            (SELECT avg(grr) FROM stg.nrr_grr WHERE beg_mrr > 0) AS mean_grr,
            (SELECT avg(payback_months) FROM stg.cac_ltv WHERE payback_months IS NOT NULL) AS mean_payback,
            (SELECT arpu FROM stg.cac_ltv ORDER BY month_start DESC LIMIT 1) AS latest_arpu,
            (SELECT sum(new_mrr) FROM stg.mrr_change) AS total_new_mrr,
            (SELECT sum(expansion_mrr) FROM stg.mrr_change) AS total_expansion_mrr,
            (SELECT sum(reactivation_mrr) FROM stg.mrr_change) AS total_reactivation_mrr,
            (SELECT sum(contraction_mrr) FROM stg.mrr_change) AS total_contraction_mrr,
            (SELECT sum(churn_mrr) FROM stg.mrr_change) AS total_churn_mrr
        """
    ).fetchone()
    keys = [
        "start_month",
        "end_month",
        "as_of_date",
        "ending_mrr",
        "ending_arr",
        "peak_arr",
        "peak_arr_month",
        "mean_nrr",
        "mean_grr",
        "mean_payback",
        "latest_arpu",
        "total_new_mrr",
        "total_expansion_mrr",
        "total_reactivation_mrr",
        "total_contraction_mrr",
        "total_churn_mrr",
    ]
    print("Metric summary")
    for key, value in zip(keys, row):
        print(f"  {key}: {value}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build local SaaS KPI warehouse from the golden Excel fixture."
    )
    parser.add_argument(
        "--as-of",
        dest="as_of",
        default=DEFAULT_AS_OF_DATE,
        type=_parse_as_of,
        help=f"Inclusive analysis cutoff (default {DEFAULT_AS_OF_DATE})",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="After a successful analytics build, generate charts and the case-study PDF.",
    )
    args = parser.parse_args(argv)

    WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if DUCKDB_PATH.exists():
        DUCKDB_PATH.unlink()
    wal_path = DUCKDB_PATH.with_suffix(".duckdb.wal")
    if wal_path.exists():
        wal_path.unlink()

    print(f"Workbook: {WORKBOOK_PATH}")
    print(f"DuckDB:   {DUCKDB_PATH}")
    print(f"As-of:    {args.as_of}")

    con = duckdb.connect(str(DUCKDB_PATH))
    try:
        row_counts = load_workbook(con)
        print("Loaded raw sheets:", row_counts)

        applied = build_models(con, as_of_date=args.as_of)
        print("Applied SQL models:", ", ".join(applied))

        results = run_validations(con)
        summary_path = write_validation_summary(results)
        failed = [r for r in results if not r.passed]

        print("Validation")
        for result in results:
            flag = "PASS" if result.passed else "FAIL"
            print(f"  [{flag}] {result.name}: {result.detail}")

        output_paths = write_outputs(con)
        print("Wrote", summary_path)
        for path in output_paths:
            print("Wrote", path)

        if failed:
            print(f"BUILD FAILED: {len(failed)} check(s) failed.")
            return 1

        _print_metric_summary(con)
        print("BUILD PASSED")

        if args.report:
            from src.build_report import build_case_study

            pdf_path = build_case_study()
            print("Wrote", pdf_path)
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
