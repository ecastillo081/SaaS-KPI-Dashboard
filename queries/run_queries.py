from pathlib import Path

from sqlalchemy import create_engine, text

from supabase.db import postgres_url

engine = create_engine(postgres_url())

sql_dir = Path("../sql")
sql_files = sorted(sql_dir.glob("*.sql"))

for sql_path in sql_files:
    print(f"Executing: {sql_path.name}")
    with open(sql_path) as f:
        ddl = f.read()
    with engine.begin() as conn:
        conn.execute(text(ddl))
