import duckdb
import pandas as pd

DATABASE_FILE_PATH = "database/ipl_analytics.duckdb"


def connect_to_db():
    return duckdb.connect(DATABASE_FILE_PATH)

