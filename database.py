import duckdb
import pandas as pd

DATABASE_FILE_PATH = "database/ipl_analytics.duckdb"


def connect_to_db():
    return duckdb.connect(DATABASE_FILE_PATH)


def execute_query(query: str, params=None) -> pd.DataFrame:
    conn = connect_to_db()

    try:
        if params:
            return conn.execute(query, params).fetch_df()
        return conn.execute(query).fetch_df()
    finally:
        conn.close()