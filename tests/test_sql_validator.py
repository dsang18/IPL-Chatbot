
import pytest

from src.utils.sql_validator import validate_sql



# Verify that a valid SELECT query is accepted and receives a row limit.
def test_valid_select_receives_row_limit():
    query = validate_sql("SELECT player_name FROM dim_player", ["dim_player"], 25)
    assert "LIMIT 25" in query.upper()


# Verify that an existing smaller row limit is preserved.
def test_existing_smaller_limit_is_preserved():
    query = validate_sql("SELECT player_name FROM dim_player LIMIT 10", ["dim_player"], 25)
    assert "LIMIT 10" in query.upper()


# Verify that queries referencing unselected tables are rejected.
def test_unselected_table_is_rejected():
    with pytest.raises(ValueError, match="selected tables"):
        validate_sql("SELECT * FROM dim_player", ["dim_team"], 25)


# Verify that write operations are rejected.
def test_delete_query_is_rejected():
    with pytest.raises(ValueError, match="read-only SELECT"):
        validate_sql("DELETE FROM dim_player", ["dim_player"], 25)


# Verify that multiple SQL statements are rejected.
def test_multiple_statements_are_rejected():
    with pytest.raises(ValueError, match="one non-empty SQL statement"):
        validate_sql("SELECT * FROM dim_player; SELECT * FROM dim_team;", ["dim_player", "dim_team"], 25)


# Verify that external file-reading functions are rejected.
def test_external_file_access_is_rejected():
    with pytest.raises(ValueError):
        validate_sql("SELECT * FROM read_csv('data.csv')", ["dim_player"], 25)


# Verify that qualified database or schema references are rejected.
def test_qualified_table_reference_is_rejected():
    with pytest.raises(ValueError, match="Qualified table references"):
        validate_sql("SELECT * FROM other_schema.dim_player", ["dim_player"], 25)
