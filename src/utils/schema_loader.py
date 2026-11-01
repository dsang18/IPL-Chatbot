
from pathlib import Path
from typing import Any

import yaml

ROOT_DIR = Path(__file__).resolve().parents[1]


# Load and validate the complete database schema.
def load_database_schema(file_path: str | Path) -> dict[str, Any]:
    schema_path = Path(file_path)
    if not schema_path.is_absolute():
        schema_path = ROOT_DIR / schema_path
    try:
        print(f"[SCHEMA] Loading database schema from {schema_path}.")
        if not schema_path.is_file():
            raise FileNotFoundError(f"Schema file does not exist: {schema_path}")
        with schema_path.open("r", encoding="utf-8") as file:
            schema = yaml.safe_load(file)
        if not isinstance(schema, dict) or not isinstance(schema.get("tables"), dict):
            raise ValueError("Schema must contain a top-level 'tables' dictionary.")
        return schema
    except Exception as error:
        raise RuntimeError(f"Unable to load database schema '{schema_path}': {error}") from error


# Return only the schema definitions for the selected tables.
def load_custom_database_schema(database_schema: dict[str, Any], tables: list[str]) -> dict[str, Any]:
    try:
        print(f"[SCHEMA] Preparing schema for {len(tables)} selected tables.")
        available_tables = database_schema.get("tables", {})
        invalid_tables = set(tables) - set(available_tables)
        if invalid_tables:
            raise ValueError(f"Unknown tables requested: {sorted(invalid_tables)}.")
        return {"tables": {table: available_tables[table] for table in tables}}
    except Exception as error:
        raise RuntimeError(f"Unable to prepare the selected database schema: {error}") from error


# Extract table descriptions and column names for the Table Selector Agent.
def get_database_schema_metadata(schema: dict[str, Any]) -> dict[str, Any]:
    try:
        metadata_schema = {}
        for table_name, details in schema["tables"].items():
            metadata_schema[table_name] = {
                "description": details.get("description", ""), 
                "columns": list(details.get("columns", {}).keys())
            }
        return metadata_schema
    except Exception as error:
        raise RuntimeError(f"Unable to extract database schema metadata: {error}") from error
