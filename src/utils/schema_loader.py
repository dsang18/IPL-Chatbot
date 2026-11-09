from pathlib import Path
from typing import Any
import re

import yaml

ROOT_DIR = Path(__file__).resolve().parents[1]


# Load and validate the complete database schema.
def load_database_schema(file_path: str | Path) -> dict[str, Any]:
    try:
        schema_path = Path(file_path)
        if not schema_path.is_absolute():
            schema_path = ROOT_DIR / schema_path

        print(f"[SCHEMA] Loading database schema from {schema_path}.")

        if not schema_path.is_file():
            raise FileNotFoundError(f"Schema file does not exist: {schema_path}")

        with schema_path.open("r", encoding="utf-8") as file:
            schema = yaml.safe_load(file)

        if not isinstance(schema, dict) or not isinstance(schema.get("tables"), dict):
            raise ValueError("Schema must contain a top-level 'tables' dictionary.")

        return schema

    except Exception as error:
        raise RuntimeError(f"Unable to load database schema '{file_path}': {error}") from error


# Extract foreign-key relationships from the column descriptions.
def extract_relationships(schema: dict[str, Any]) -> list[dict[str, str]]:
    try:
        relationships = []

        for table_name, details in schema["tables"].items():
            for column_name, column in details.get("columns", {}).items():
                description = column.get("description", "")
                match = re.search(
                    r"references\s+([a-zA-Z_][\w]*)\.([a-zA-Z_][\w]*)",
                    description,
                    re.IGNORECASE
                )

                if match:
                    relationships.append({
                        "from_table": table_name,
                        "from_column": column_name,
                        "to_table": match.group(1),
                        "to_column": match.group(2)
                    })

        return relationships

    except Exception as error:
        raise RuntimeError(f"Unable to extract schema relationships: {error}") from error


# Return complete metadata for the Table Selector and Query Planner.
def get_database_schema_metadata(schema: dict[str, Any]) -> dict[str, Any]:
    try:
        print("[SCHEMA] Extracting enriched schema metadata.")

        metadata = {}

        for table_name, details in schema["tables"].items():
            columns = {}

            for column_name, column in details.get("columns", {}).items():
                columns[column_name] = {
                    "type": column.get("type", "UNKNOWN"),
                    "description": column.get("description", "")
                }

            metadata[table_name] = {
                "description": details.get("description", ""),
                "grain": schema.get("table_grains", {}).get(
                    table_name, "Not explicitly documented."
                ),
                "primary_key": schema.get("table_keys", {}).get(
                    table_name, details.get("primary_key")
                ),
                "columns": columns
            }

        return {
            "tables": metadata,
            "relationships": extract_relationships(schema)
        }

    except Exception as error:
        raise RuntimeError(f"Unable to extract database schema metadata: {error}") from error


# Return only the schema definitions and relationships for selected tables.
def load_custom_database_schema(database_schema: dict[str, Any], tables: list[str]) -> dict[str, Any]:
    try:
        print(f"[SCHEMA] Preparing schema for {len(tables)} selected tables.")

        available_tables = database_schema.get("tables", {})
        invalid_tables = set(tables) - set(available_tables)

        if invalid_tables:
            raise ValueError(f"Unknown tables requested: {sorted(invalid_tables)}.")

        selected_relationships = [
            relationship
            for relationship in extract_relationships(database_schema)
            if relationship["from_table"] in tables
            and relationship["to_table"] in tables
        ]

        return {
            "tables": {table: available_tables[table] for table in tables},
            "relationships": selected_relationships
        }

    except Exception as error:
        raise RuntimeError(f"Unable to prepare the selected database schema: {error}") from error


# Build a lightweight schema catalogue for the Query Planner.
def get_query_planner_schema(schema: dict[str, Any]) -> dict[str, Any]:
    try:
        print("[SCHEMA] Building compact schema for Query Planner.")

        metadata = get_database_schema_metadata(schema)

        return {
            table_name: {
                "description": details["description"][:150],
                "grain": details["grain"],
                "columns": list(details["columns"].keys())
            }
            for table_name, details in metadata["tables"].items()
        }

    except Exception as error:
        raise RuntimeError(f"Unable to build Query Planner schema: {error}") from error


# Build a compact schema for the Table Selector, retaining types and relationships.
def get_table_selector_schema(schema: dict[str, Any]) -> dict[str, Any]:
    try:
        print("[SCHEMA] Building compact schema for Table Selector.")

        metadata = get_database_schema_metadata(schema)

        tables = {
            table_name: {
                "description": details["description"][:150],
                "grain": details["grain"],
                "columns": {
                    column_name: column_details["type"]
                    for column_name, column_details in details["columns"].items()
                },
                "primary_key": details["primary_key"]
            }
            for table_name, details in metadata["tables"].items()
        }

        return {
            "tables": tables,
            "relationships": metadata["relationships"]
        }

    except Exception as error:
        raise RuntimeError(f"Unable to build Table Selector schema: {error}") from error