import yaml

def load_database_schema(file_path):
    """
    Load the database schema from a YAML file.

    Args:
        file_path (str): The path to the YAML file containing the database schema.
    """
    print(f"Loading database schema from {file_path}...")
    with open(file_path, 'r') as file:
        schema = yaml.safe_load(file)
    return schema


def load_custom_database_schema(database_schema:dict, tables:list) -> dict:
    """
    Load a custom database schema based on the provided tables.

    Args:
        database_schema (dict): The complete database schema.
        tables (list): A list of table names to include in the custom schema.

    Returns:
        dict: A custom database schema containing only the specified tables.
    """
    custom_schema = {"tables": {}}
    for table in tables:
        if table in database_schema['tables']:
            custom_schema['tables'][table] = database_schema['tables'][table]
        else:
            print(f"Warning: Table '{table}' not found in the database schema.")
    return custom_schema


def get_database_schema_metadata(schema):

    metadata_schema = {}

    for table_name, details in schema['tables'].items():
        metadata_schema[table_name] = {
            "description": details.get("description", ""),
            "columns": list(details.get("columns", {}).keys())
        }

    return metadata_schema



