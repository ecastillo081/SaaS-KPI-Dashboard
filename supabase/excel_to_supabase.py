import re
import pandas as pd
from slugify import slugify
from sqlalchemy import create_engine, text
from supabase.credentials import username, password, host, port, database

# =========================
# CONFIG
# =========================
# Excel workbook path
EXCEL_PATH = "../data/saas_kpi_seeds.xlsx"  # revise as needed

# Target schema in Supabase/Postgres
PUSH_SCHEMA = "raw"

# =========================
# HELPERS
# =========================
def sanitize_table_name(name: str) -> str:
    """Lowercase, alnum/underscore only, safe for Postgres table names."""
    s = slugify(name, separator="_", lowercase=True)
    if not re.match(r"^[a-z]", s or ""):
        s = f"t_{s}" if s else "t_sheet"
    reserved = {"user", "order", "select", "table", "group", "where"}
    if s in reserved:
        s = f"{s}_t"
    return s

def snake_case_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Slugify columns, ensure uniqueness, avoid empties."""
    df = df.copy()
    new_cols = []
    seen = set()
    for i, c in enumerate(df.columns):
        base = slugify(str(c), separator="_", lowercase=True) or f"col_{i+1}"
        col = base
        suffix = 1
        while col in seen:
            suffix += 1
            col = f"{base}_{suffix}"
        seen.add(col)
        new_cols.append(col)
    df.columns = new_cols
    return df

def coerce_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Try to get nice dtypes (esp. dates)."""
    df = df.copy()
    for c in df.columns:
        if any(key in c for key in ("date", "dt", "timestamp", "time")):
            try:
                df[c] = pd.to_datetime(df[c], errors="ignore", utc=False)
            except Exception:
                pass
    return df.convert_dtypes()

# Optional renaming map
SHEET_MAP = {
    # "Google Ads Daily": "google_ads_daily",
    # "Meta Ads Daily": "meta_ads_daily",
}

# =========================
# READ EXCEL
# =========================
all_sheets = pd.read_excel(EXCEL_PATH, sheet_name=None, engine="openpyxl")

dataframes = {}
for sheet_name, df in all_sheets.items():
    if df is None or df.dropna(how="all").empty:
        continue
    df = snake_case_columns(df)
    df = coerce_dtypes(df)
    tbl = SHEET_MAP.get(sheet_name, sanitize_table_name(sheet_name))
    dataframes[tbl] = df

if not dataframes:
    raise RuntimeError("No non-empty sheets found in the Excel file.")

# =========================
# PUSH TO SUPABASE
# =========================
connection_string = (
    f"postgresql://{username}:{password}@{host}:{port}/{database}?sslmode=require"
)
engine = create_engine(connection_string, pool_pre_ping=True, future=True)

# Ensure schema exists
with engine.begin() as conn:
    conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{PUSH_SCHEMA}";'))

for table_name, df in dataframes.items():
    try:
        df.to_sql(
            name=table_name,
            con=engine,
            schema=PUSH_SCHEMA,
            if_exists="replace",   # use "append" if you don’t want to overwrite
            index=False,
            chunksize=10_000,
        )
        print(f"✓ Pushed {table_name} → {PUSH_SCHEMA} ({len(df)} rows)")
    except Exception as e:
        print(f"✗ Error pushing {table_name}: {e}")
