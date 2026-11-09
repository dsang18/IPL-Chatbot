
from pathlib import Path

import duckdb

ROOT_DIR = Path(__file__).resolve().parents[2]
DATABASE_FILE_PATH = ROOT_DIR / "database" / "ipl_analytics.duckdb"

print(f"Database File Path : {DATABASE_FILE_PATH}")


# Establish a read-only DuckDB connection with external access disabled.
def connect_to_db() -> duckdb.DuckDBPyConnection:
    try:
        print(f"[DATABASE] Connecting to {DATABASE_FILE_PATH}.")
        if not DATABASE_FILE_PATH.is_file():
            raise FileNotFoundError(f"DuckDB database does not exist: {DATABASE_FILE_PATH}")
        return duckdb.connect(
            database=str(DATABASE_FILE_PATH), 
            read_only=True, 
            config={"enable_external_access": "false"}
        )
    except Exception as error:
        raise RuntimeError(f"Unable to establish a secure DuckDB connection: {error}") from error
