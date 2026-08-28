"""Apply SQL models to the local DuckDB database."""

from __future__ import annotations

from pathlib import Path

from src.settings import DEFAULT_AS_OF_DATE, SQL_DIR


def _sql_files(sql_dir: Path) -> list[Path]:
    return sorted(sql_dir.glob("*.sql"))


def _render_sql(sql_text: str, as_of_date: str) -> str:
    return sql_text.replace("{{AS_OF_DATE}}", as_of_date)


def _has_statement(sql_text: str) -> bool:
    stripped = "\n".join(
        line for line in sql_text.splitlines() if not line.strip().startswith("--")
    ).strip()
    return bool(stripped)


def build_models(con, as_of_date: str = DEFAULT_AS_OF_DATE, sql_dir: Path | None = None) -> list[str]:
    directory = Path(sql_dir) if sql_dir is not None else SQL_DIR
    con.execute("CREATE SCHEMA IF NOT EXISTS stg")
    applied: list[str] = []

    for path in _sql_files(directory):
        sql_text = _render_sql(path.read_text(encoding="utf-8"), as_of_date)
        if not _has_statement(sql_text):
            continue
        con.execute(sql_text)
        applied.append(path.name)

    return applied
