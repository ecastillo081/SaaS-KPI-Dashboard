import os

REQUIRED = ("PGUSER", "PGPASSWORD", "PGHOST", "PGPORT", "PGDATABASE")


def postgres_url():
    missing = [key for key in REQUIRED if not os.environ.get(key)]
    if missing:
        raise RuntimeError(
            "Set database credentials as environment variables, not in source files: "
            + ", ".join(missing)
        )
    return (
        "postgresql://{user}:{password}@{host}:{port}/{database}?sslmode=require".format(
            user=os.environ["PGUSER"],
            password=os.environ["PGPASSWORD"],
            host=os.environ["PGHOST"],
            port=os.environ["PGPORT"],
            database=os.environ["PGDATABASE"],
        )
    )
