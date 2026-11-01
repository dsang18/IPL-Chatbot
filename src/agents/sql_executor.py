
from threading import Timer

import pandas as pd

from src.utils.database import connect_to_db
from src.utils.sql_validator import validate_sql


class SQLExecutor:

    # Configure SQL execution limits.
    def __init__(self, max_rows: int = 500, timeout_seconds: int = 20):
        self.max_rows = max_rows
        self.timeout_seconds = timeout_seconds

    # Validate and execute a read-only SQL query against the selected tables.
    def run(self, query: str, allowed_tables: list[str]) -> pd.DataFrame:
        connection = None
        cursor = None
        timeout_timer = None
        try:
            print("[SQL EXECUTOR] Starting SQL execution.")

            # Initialize the database connection and validate the sql query
            validated_query = validate_sql(query, allowed_tables, self.max_rows)
            connection = connect_to_db()
            cursor = connection.cursor()
            timeout_timer = Timer(self.timeout_seconds, connection.interrupt)

            # Start the timer
            timeout_timer.start()
            print(f"[SQL EXECUTOR] Executing query with a {self.timeout_seconds}-second timeout.")
            
            # Execute the query
            cursor.execute(validated_query)
            result = cursor.fetch_df()

            # Check if the output is within range
            if len(result) > self.max_rows:
                raise ValueError(f"Query returned {len(result)} rows, exceeding the {self.max_rows}-row limit.")
            print(f"[SQL EXECUTOR] Execution completed. Rows returned: {len(result)}.")

            return result

        except Exception as error:
            raise RuntimeError(f"SQL execution failed. Check query validity, selected tables and execution timeout: {error}") from error
        
        finally:
            if timeout_timer:
                timeout_timer.cancel()
            if cursor:
                cursor.close()
            if connection:
                connection.close()
