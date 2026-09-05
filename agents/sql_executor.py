import pandas as pd
from utils.database import connect_to_db

class SQLExecutor:
    def __init__(self):
        self.conn = connect_to_db()

    def run(self, query: str, params=None) -> pd.DataFrame:
        conn = self.conn.cursor()

        try:
            if params:
                return conn.execute(query, params).fetch_df()
            return conn.execute(query).fetch_df()
        finally:
            conn.close()
