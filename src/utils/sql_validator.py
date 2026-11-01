
import re

import sqlglot
from sqlglot import exp

BLOCKED_FUNCTIONS = {
    "READ_CSV", "READ_CSV_AUTO", "READ_PARQUET", "READ_JSON",
    "READ_JSON_AUTO", "READ_BLOB", "READ_TEXT", "PARQUET_SCAN",
    "CSV_SCAN", "GLOB", "QUERY", "QUERY_TABLE", "SQLITE_SCAN",
    "POSTGRES_SCAN", "MYSQL_SCAN"
}


# Validate generated SQL and enforce the selected-table and row-limit restrictions.
def validate_sql(query: str, allowed_tables: list[str], max_rows: int = 500) -> str:
    try:
        print("[SQL VALIDATOR] Validating generated SQL.")
        if not query or not query.strip():
            raise ValueError("The generated SQL query is empty.")
        if len(query) > 20000:
            raise ValueError("The generated SQL query exceeds the 20,000-character limit.")
        if max_rows < 1:
            raise ValueError("The maximum row limit must be greater than zero.")

        cleaned_query = re.sub(
            r"^```(?:sql)?\s*|```$", "", 
            query.strip(), 
            flags=re.IGNORECASE | re.MULTILINE).strip()
        statements = sqlglot.parse(cleaned_query, read="duckdb")

        # Check if the query is legit
        if len(statements) != 1 or statements[0] is None:
            raise ValueError("Exactly one non-empty SQL statement is allowed.")

        parsed_query = statements[0]
        if not isinstance(parsed_query, exp.Query):
            raise ValueError(f"Only read-only SELECT queries are permitted. Received: {type(parsed_query).__name__}.")

        cte_names = {cte.alias_or_name.lower() for cte in parsed_query.find_all(exp.CTE)}
        allowed_names = {table.lower() for table in allowed_tables}
        referenced_tables = set()

        # Check if any qualified tables are referenced in the query
        for table in parsed_query.find_all(exp.Table):
            if table.db or table.catalog:
                raise ValueError(f"Qualified table references are not permitted: {table.sql()}.")
            table_name = table.name.lower()
            if table_name not in cte_names:
                referenced_tables.add(table_name)

        # Check if any table is reference apart from allowed tables
        invalid_tables = referenced_tables - allowed_names
        if invalid_tables:
            raise ValueError(f"Query references tables that were not selected: {sorted(invalid_tables)}.")

        for function in parsed_query.find_all(exp.Func):
            function_name = function.name.upper() if isinstance(function, exp.Anonymous) else function.sql_name().upper()
            if function_name in BLOCKED_FUNCTIONS:
                raise ValueError(f"External data access function '{function_name}' is not permitted.")

        # Check if LIMIT in SQL Query is within the range of max_rows
        existing_limit = parsed_query.args.get("limit")
        requested_limit = None
        if existing_limit is not None:
            limit_expression = existing_limit.expression
            if isinstance(limit_expression, exp.Literal) and limit_expression.is_int:
                requested_limit = int(limit_expression.this)

        if requested_limit is None or requested_limit > max_rows:
            parsed_query = parsed_query.limit(max_rows)

        # Return the validated query if no discrepancies found
        validated_query = parsed_query.sql(dialect="duckdb")
        print(f"[SQL VALIDATOR] Query accepted. Tables: {sorted(referenced_tables)}. Maximum rows: {max_rows}.")
        return validated_query
    except Exception as error:
        raise ValueError(f"SQL validation failed. Only one read-only SELECT against the selected tables is allowed: {error}") from error
