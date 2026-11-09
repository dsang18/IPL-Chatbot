import re

import sqlglot
from sqlglot import exp

BLOCKED_FUNCTIONS = {
    "READ_CSV", "READ_CSV_AUTO", "READ_PARQUET", "READ_JSON",
    "READ_JSON_AUTO", "READ_BLOB", "READ_TEXT", "PARQUET_SCAN",
    "CSV_SCAN", "GLOB", "QUERY", "QUERY_TABLE", "SQLITE_SCAN",
    "POSTGRES_SCAN", "MYSQL_SCAN"
}


# Validate SQL table and column references against the selected schema.
def validate_schema_references(parsed_query: exp.Expression, database_schema: dict) -> None:
    try:
        tables_schema = database_schema.get("tables", {})
        if not tables_schema:
            raise ValueError("Selected database schema is empty.")

        cte_names = {
            cte.alias_or_name.lower()
            for cte in parsed_query.find_all(exp.CTE)
        }

        derived_aliases = {
            subquery.alias_or_name.lower()
            for subquery in parsed_query.find_all(exp.Subquery)
            if subquery.alias_or_name
        }

        table_aliases = {}
        referenced_tables = set()

        for table in parsed_query.find_all(exp.Table):
            if table.db or table.catalog:
                raise ValueError(f"Qualified table references are not permitted: {table.sql()}.")

            table_name = table.name.lower()

            if table_name in cte_names:
                continue

            if table_name not in {name.lower() for name in tables_schema}:
                raise ValueError(f"Table '{table_name}' does not exist in the selected schema.")

            actual_table = next(
                name for name in tables_schema if name.lower() == table_name
            )

            referenced_tables.add(actual_table)
            table_aliases[table.alias_or_name.lower()] = actual_table
            table_aliases[table_name] = actual_table

        if not referenced_tables:
            raise ValueError("Query must reference at least one selected database table.")

        columns_by_table = {
            table: {column.lower() for column in details.get("columns", {})}
            for table, details in tables_schema.items()
        }

        all_columns = set().union(
            *(columns_by_table[table] for table in referenced_tables)
        )

        projection_aliases = set()

        for select in parsed_query.find_all(exp.Select):
            for projection in select.expressions:
                if isinstance(projection, exp.Alias):
                    projection_aliases.add(projection.alias.lower())

        for column in parsed_query.find_all(exp.Column):
            column_name = column.name.lower()

            if column_name == "*":
                continue

            qualifier = column.table.lower() if column.table else None

            if qualifier in cte_names or qualifier in derived_aliases:
                continue

            if qualifier:
                if qualifier not in table_aliases:
                    raise ValueError(
                        f"Unknown table alias '{qualifier}' used for column '{column_name}'."
                    )

                actual_table = table_aliases[qualifier]

                if column_name not in columns_by_table[actual_table]:
                    raise ValueError(
                        f"Column '{column.name}' does not exist in table '{actual_table}'."
                    )

            elif column_name not in all_columns and column_name not in projection_aliases:
                raise ValueError(
                    f"Column '{column.name}' does not exist in the selected tables."
                )

    except Exception as error:
        raise ValueError(f"Schema reference validation failed: {error}") from error


# Validate generated SQL and enforce read-only, table and row-limit restrictions.
def validate_sql(query: str, allowed_tables: list[str], max_rows: int = 500, database_schema: dict | None = None) -> str:
    try:
        print("[SQL VALIDATOR] Validating generated SQL.")

        if not query or not query.strip():
            raise ValueError("The generated SQL query is empty.")

        if len(query) > 20000:
            raise ValueError("The generated SQL query exceeds the 20,000-character limit.")

        if not allowed_tables:
            raise ValueError("At least one allowed table must be provided.")

        if max_rows < 1:
            raise ValueError("The maximum row limit must be greater than zero.")

        cleaned_query = re.sub(
            r"^```(?:sql)?\s*|```$",
            "",
            query.strip(),
            flags=re.IGNORECASE | re.MULTILINE
        ).strip()

        statements = sqlglot.parse(cleaned_query, read="duckdb")

        if len(statements) != 1 or statements[0] is None:
            raise ValueError("Exactly one non-empty SQL statement is allowed.")

        parsed_query = statements[0]

        if not isinstance(parsed_query, exp.Query):
            raise ValueError(
                f"Only read-only SELECT queries are permitted. Received: {type(parsed_query).__name__}."
            )

        cte_names = {
            cte.alias_or_name.lower()
            for cte in parsed_query.find_all(exp.CTE)
        }

        allowed_names = {table.lower() for table in allowed_tables}
        referenced_tables = set()

        for table in parsed_query.find_all(exp.Table):
            if table.db or table.catalog:
                raise ValueError(f"Qualified table references are not permitted: {table.sql()}.")

            table_name = table.name.lower()

            if table_name not in cte_names:
                referenced_tables.add(table_name)

        invalid_tables = referenced_tables - allowed_names

        if invalid_tables:
            raise ValueError(
                f"Query references tables that were not selected: {sorted(invalid_tables)}."
            )

        if not referenced_tables:
            raise ValueError("Query must reference at least one selected database table.")

        for function in parsed_query.find_all(exp.Func):
            function_name = (
                function.name.upper()
                if isinstance(function, exp.Anonymous)
                else function.sql_name().upper()
            )

            if function_name in BLOCKED_FUNCTIONS:
                raise ValueError(
                    f"External data access function '{function_name}' is not permitted."
                )

        if database_schema is not None:
            validate_schema_references(parsed_query, database_schema)

        existing_limit = parsed_query.args.get("limit")
        requested_limit = None

        if existing_limit is not None:
            limit_expression = existing_limit.expression

            if isinstance(limit_expression, exp.Literal) and limit_expression.is_int:
                requested_limit = int(limit_expression.this)

        if requested_limit is None or requested_limit > max_rows:
            parsed_query = parsed_query.limit(max_rows)

        validated_query = parsed_query.sql(dialect="duckdb")

        print(
            f"[SQL VALIDATOR] Query accepted. "
            f"Tables: {sorted(referenced_tables)}. Maximum rows: {max_rows}."
        )

        return validated_query

    except Exception as error:
        raise ValueError(
            f"SQL validation failed. Only one read-only SELECT against the selected tables is allowed: {error}"
        ) from error