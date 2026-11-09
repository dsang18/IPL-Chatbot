from threading import Timer

import pandas as pd

from src.utils.database import connect_to_db
from src.utils.sql_validator import validate_sql


class SQLExecutor:

    # Configure SQL execution limits.
    def __init__(self, max_rows: int = 500, timeout_seconds: int = 20):
        self.max_rows = max_rows
        self.timeout_seconds = timeout_seconds

    # Validate and execute SQL against the selected database schema.
    def run(self, query: str, allowed_tables: list[str], database_schema: dict) -> pd.DataFrame:
        connection = None
        cursor = None
        timeout_timer = None

        try:
            print("[SQL EXECUTOR] Starting SQL execution.")

            validated_query = validate_sql(
                query=query,
                allowed_tables=allowed_tables,
                max_rows=self.max_rows,
                database_schema=database_schema
            )

            connection = connect_to_db()
            cursor = connection.cursor()

            timeout_timer = Timer(self.timeout_seconds, connection.interrupt)
            timeout_timer.start()

            print(f"[VALIDATED QUERY] {validated_query}")

            print(
                f"[SQL EXECUTOR] Executing query with a "
                f"{self.timeout_seconds}-second timeout."
            )

            cursor.execute(validated_query)
            result = cursor.fetch_df()

            if len(result) > self.max_rows:
                raise ValueError(
                    f"Query returned {len(result)} rows, exceeding the {self.max_rows}-row limit."
                )

            print(
                f"[SQL EXECUTOR] Execution completed. Rows returned: {len(result)}."
            )

            return result

        except Exception as error:
            raise RuntimeError(
                f"SQL execution failed. Query: {query[:1000]}. Error: {error}"
            ) from error

        finally:
            if timeout_timer:
                timeout_timer.cancel()

            if cursor:
                cursor.close()

            if connection:
                connection.close()