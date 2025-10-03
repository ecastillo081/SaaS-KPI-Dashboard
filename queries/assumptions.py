from sqlalchemy import create_engine, text
from supabase.credentials import username, password, host, port, database

# Create database engine
connection_string = f"postgresql://{username}:{password}@{host}:{port}/{database}?sslmode=require"
engine = create_engine(connection_string)

sql_path = "../sql/00_assumptions.sql"

# Load SQL file
with open(sql_path) as f:
    ddl = f.read()

# Execute
with engine.begin() as conn:
    conn.execute(text(ddl))
