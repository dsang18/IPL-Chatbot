import pytest

from src.utils.sql_validator import validate_sql


@pytest.fixture
def database_schema():
    return {
        "tables": {
            "dim_player": {
                "columns": {
                    "player_id": {"type": "INTEGER"},
                    "player_name": {"type": "VARCHAR"}
                }
            },
            "agg_player_batting": {
                "columns": {
                    "player_id": {"type": "INTEGER"},
                    "runs": {"type": "INTEGER"},
                    "balls": {"type": "INTEGER"},
                    "strike_rate": {"type": "FLOAT"}
                }
            }
        }
    }


# Verify that a valid SELECT query is accepted and receives a row limit.
def test_valid_select_receives_row_limit(database_schema):
    query = validate_sql(
        "SELECT player_name FROM dim_player",
        ["dim_player"],
        25,
        database_schema
    )
    assert "LIMIT 25" in query.upper()


# Verify that an existing smaller row limit is preserved.
def test_existing_smaller_limit_is_preserved(database_schema):
    query = validate_sql(
        "SELECT player_name FROM dim_player LIMIT 10",
        ["dim_player"],
        25,
        database_schema
    )
    assert "LIMIT 10" in query.upper()


# Verify that queries referencing unselected tables are rejected.
def test_unselected_table_is_rejected(database_schema):
    with pytest.raises(ValueError, match="selected tables"):
        validate_sql(
            "SELECT player_name FROM dim_player",
            ["agg_player_batting"],
            25,
            database_schema
        )


# Verify that write operations are rejected.
def test_delete_query_is_rejected(database_schema):
    with pytest.raises(ValueError, match="read-only SELECT"):
        validate_sql(
            "DELETE FROM dim_player",
            ["dim_player"],
            25,
            database_schema
        )


# Verify that multiple SQL statements are rejected.
def test_multiple_statements_are_rejected(database_schema):
    with pytest.raises(ValueError, match="one non-empty SQL statement"):
        validate_sql(
            "SELECT * FROM dim_player; SELECT * FROM agg_player_batting;",
            ["dim_player", "agg_player_batting"],
            25,
            database_schema
        )


# Verify that external file-reading functions are rejected.
def test_external_file_access_is_rejected(database_schema):
    with pytest.raises(ValueError, match="External data access"):
        validate_sql(
            "SELECT * FROM read_csv('data.csv')",
            ["dim_player"],
            25,
            database_schema
        )


# Verify that qualified database or schema references are rejected.
def test_qualified_table_reference_is_rejected(database_schema):
    with pytest.raises(ValueError, match="Qualified table references"):
        validate_sql(
            "SELECT * FROM other_schema.dim_player",
            ["dim_player"],
            25,
            database_schema
        )


# Verify that nonexistent columns are rejected.
def test_invalid_column_is_rejected(database_schema):
    with pytest.raises(ValueError, match="does not exist"):
        validate_sql(
            "SELECT total_runs FROM dim_player",
            ["dim_player"],
            25,
            database_schema
        )


# Verify that valid table aliases are supported.
def test_valid_table_alias_is_accepted(database_schema):
    query = validate_sql(
        "SELECT p.player_name FROM dim_player p",
        ["dim_player"],
        25,
        database_schema
    )
    assert "PLAYER_NAME" in query.upper()


# Verify that invalid qualified columns are rejected.
def test_invalid_qualified_column_is_rejected(database_schema):
    with pytest.raises(ValueError, match="does not exist"):
        validate_sql(
            "SELECT p.total_runs FROM dim_player p",
            ["dim_player"],
            25,
            database_schema
        )


# Verify that CTEs referencing selected tables are supported.
def test_cte_query_is_accepted(database_schema):
    query = validate_sql(
        """
        WITH player_data AS (
            SELECT player_name FROM dim_player
        )
        SELECT player_name FROM player_data
        """,
        ["dim_player"],
        25,
        database_schema
    )
    assert "WITH" in query.upper()


# Verify that queries without physical database tables are rejected.
def test_query_without_table_reference_is_rejected(database_schema):
    with pytest.raises(ValueError, match="at least one selected database table"):
        validate_sql(
            "SELECT 1",
            ["dim_player"],
            25,
            database_schema
        )


# Verify that a valid aggregate query is accepted.
def test_valid_aggregate_query_is_accepted(database_schema):
    query = validate_sql(
        """
        SELECT player_id, SUM(runs) AS total_runs
        FROM agg_player_batting
        GROUP BY player_id
        ORDER BY total_runs DESC
        """,
        ["agg_player_batting"],
        25,
        database_schema
    )
    assert "SUM" in query.upper()