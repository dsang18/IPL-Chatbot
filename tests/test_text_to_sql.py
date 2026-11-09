import pytest

from src.utils.schema_loader import (
    load_database_schema,
    load_custom_database_schema
)
from src.utils.sql_validator import validate_sql


@pytest.fixture
def schema():
    try:
        return load_database_schema("database/database_schema.yaml")
    except Exception as error:
        raise RuntimeError(f"Unable to load schema for SQL evaluation: {error}") from error


# Verify that a player batting ranking uses the correct aggregate and dimension tables.
def test_player_batting_ranking(schema):
    tables = ["agg_player_batting", "dim_player"]
    selected_schema = load_custom_database_schema(schema, tables)

    query = """
        SELECT p.player_name, SUM(b.runs) AS total_runs
        FROM agg_player_batting b
        JOIN dim_player p ON b.player_id = p.player_id
        GROUP BY p.player_name
        ORDER BY total_runs DESC
        LIMIT 5
    """

    validated = validate_sql(query, tables, 500, selected_schema)
    assert "AGG_PLAYER_BATTING" in validated.upper()


# Verify that a bowling ranking uses the correct bowling metric.
def test_bowler_wicket_ranking(schema):
    tables = ["agg_player_bowling", "dim_player"]
    selected_schema = load_custom_database_schema(schema, tables)

    query = """
        SELECT p.player_name, SUM(b.wickets) AS total_wickets
        FROM agg_player_bowling b
        JOIN dim_player p ON b.player_id = p.player_id
        GROUP BY p.player_name
        ORDER BY total_wickets DESC
        LIMIT 5
    """

    validated = validate_sql(query, tables, 500, selected_schema)
    assert "AGG_PLAYER_BOWLING" in validated.upper()


# Verify that team season comparisons use documented relationships.
def test_team_season_comparison(schema):
    tables = ["agg_team", "dim_team", "dim_season"]
    selected_schema = load_custom_database_schema(schema, tables)

    query = """
        SELECT t.team_name, s.season, a.wins
        FROM agg_team a
        JOIN dim_team t ON a.team_id = t.team_id
        JOIN dim_season s ON a.season_id = s.season_id
        ORDER BY s.season, a.wins DESC
    """

    validated = validate_sql(query, tables, 500, selected_schema)
    assert "DIM_SEASON" in validated.upper()


# Verify that a query cannot reference an invented column.
def test_invalid_metric_is_rejected(schema):
    tables = ["agg_player_batting"]
    selected_schema = load_custom_database_schema(schema, tables)

    with pytest.raises(ValueError, match="does not exist"):
        validate_sql(
            "SELECT total_runs FROM agg_player_batting",
            tables,
            500,
            selected_schema
        )