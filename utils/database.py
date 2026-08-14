from pathlib import Path

import duckdb
import pandas as pd
from utils.schema_loader import load_database_schema
import sqlglot
from sqlglot import exp

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


def validate_query(query:str, schema_file_path:Path)->dict:
    """
    Validate the SQL query by checking its syntax and structure.
    """

    schema = load_database_schema(schema_file_path)
    tables = schema['tables']
    errors = []

    try:
        statements = sqlglot.parse(query, read="duckdb")
    except Exception as e:
        return {
            "valid": False,
            "errors": [f"Invalid SQL syntax: {e}"]
        }

    if len(statements) != 1:
        errors.append("Only one SQL statement is allowed.")

    if not statements:
        return {
            "valid": False,
            "errors": ["Empty SQL query."]
        }

    statement = statements[0]

     # ---------------------------------------------------------
    # 3. Read-only / SELECT check
    # ---------------------------------------------------------
    if not isinstance(statement, (exp.Select, exp.Union)):
        errors.append(
            "Query must be read-only and contain only SELECT."
        )

    # ---------------------------------------------------------
    # 4. Validate tables
    # ---------------------------------------------------------
    used_tables = set()

    for table in statement.find_all(exp.Table):

        table_name = table.name

        used_tables.add(table_name)

        if table_name not in tables.keys():
            errors.append(
                f"Unknown table: {table_name}"
            )

    # ---------------------------------------------------------
    # 5. Build column metadata
    # ---------------------------------------------------------
    table_columns = {}

    for table_name, table_info in tables.items():

        columns = table_info.get("columns", {})

        if isinstance(columns, dict):
            table_columns[table_name] = set(
                columns.keys()
            )

        elif isinstance(columns, list):
            table_columns[table_name] = set(columns)

    # ---------------------------------------------------------
    # 6. Validate columns
    # ---------------------------------------------------------
    aliases = {}

    # Aliases for tables in the FROM clause
    for table in statement.find_all(exp.Table):
        table_name = table.name
        alias = table.alias
        if alias:
            aliases[alias] = table_name

    # Aliases for columns in the SELECT clause
    select_aliases = set()
    for select_expression in statement.expressions:
        if isinstance(select_expression, exp.Alias):
            select_aliases.add(select_expression.alias)


    for column in statement.find_all(exp.Column):

        column_name = column.name
        table_alias = column.table

        if not table_alias and column_name in select_aliases:
            continue
    
        # Qualified column:
        # dp.player_name
        if table_alias:

            actual_table = aliases.get(
                table_alias,
                table_alias
            )

            if actual_table not in table_columns:
                errors.append(
                    f"Unknown table/alias: {table_alias}"
                )
                continue

            if column_name not in table_columns[actual_table]:
                errors.append(
                    f"Unknown column "
                    f"'{column_name}' in table "
                    f"'{actual_table}'"
                )

        # Unqualified column:
        # player_name
        else:

            matching_tables = [
                table_name
                for table_name in used_tables
                if column_name in table_columns.get(
                    table_name, set()
                )
            ]

            if not matching_tables:

                errors.append(
                    f"Unknown column: {column_name}"
                )

            # elif len(matching_tables) > 1:

            #     errors.append(
            #         f"Ambiguous column: {column_name}"
            #     )


    # ---------------------------------------------------------
    # Result
    # ---------------------------------------------------------
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "tables_used": sorted(used_tables)
    }


