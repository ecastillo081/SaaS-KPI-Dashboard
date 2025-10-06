from sqlalchemy import create_engine, text
from supabase.credentials import username, password, host, port, database
from pathlib import Path

# --- Create database engine ---
connection_string = f"postgresql://{username}:{password}@{host}:{port}/{database}?sslmode=require"
engine = create_engine(connection_string)

# --- Define SQL directory and file order ---
sql_dir = Path("../sql")
sql_files = sorted(sql_dir.glob("*.sql"))  # sorts alphabetically

for sql_path in sql_files:
    print(f"Executing: {sql_path.name}")
    with open(sql_path) as f:
        ddl = f.read()
    with engine.begin() as conn:
        conn.execute(text(ddl))
