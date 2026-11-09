from src.utils.schema_loader import (
    extract_relationships,
    get_database_schema_metadata,
    load_custom_database_schema
)


# Verify that schema metadata includes types, descriptions and grain.
def test_schema_metadata_contains_complete_column_information():
    schema = {
        "tables": {
            "dim_player": {
                "description": "Player information.",
                "primary_key": "player_id",
                "columns": {
                    "player_id": {
                        "type": "INTEGER",
                        "description": "Unique player identifier."
                    },
                    "player_name": {
                        "type": "VARCHAR",
                        "description": "Player name."
                    }
                }
            }
        },
        "table_grains": {
            "dim_player": "One row per player."
        }
    }

    metadata = get_database_schema_metadata(schema)

    player = metadata["tables"]["dim_player"]

    assert player["grain"] == "One row per player."
    assert player["primary_key"] == "player_id"
    assert player["columns"]["player_id"]["type"] == "INTEGER"
    assert player["columns"]["player_name"]["description"] == "Player name."


# Verify that foreign-key relationships are extracted.
def test_foreign_key_relationships_are_extracted():
    schema = {
        "tables": {
            "fact_delivery": {
                "columns": {
                    "match_id": {
                        "type": "INTEGER",
                        "description": "References dim_match.match_id."
                    }
                }
            },
            "dim_match": {
                "columns": {
                    "match_id": {
                        "type": "INTEGER",
                        "description": "Unique match identifier."
                    }
                }
            }
        }
    }

    relationships = extract_relationships(schema)

    assert relationships == [{
        "from_table": "fact_delivery",
        "from_column": "match_id",
        "to_table": "dim_match",
        "to_column": "match_id"
    }]


# Verify that selected schema contains only relevant relationships.
def test_custom_schema_filters_relationships():
    schema = {
        "tables": {
            "fact_delivery": {"columns": {}},
            "dim_match": {"columns": {}},
            "dim_player": {"columns": {}}
        }
    }

    custom_schema = load_custom_database_schema(
        schema,
        ["fact_delivery", "dim_match"]
    )

    assert set(custom_schema["tables"]) == {"fact_delivery", "dim_match"}
    assert custom_schema["relationships"] == []