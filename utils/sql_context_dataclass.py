from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

@dataclass
class SQLAgentContext:
    user_question: str

    selected_tables: list[str] = field(default_factory=list)
    generated_sql: str = field(default_factory=str)
    validation_errors: list[str] = field(default_factory=list)
    is_valid: bool = False

    prompt_paths: dict = field(default_factory=lambda:{
        "sql_query_system_prompt": Path("prompts/sql_system_prompt.txt"),
        "sql_query_user_prompt": Path("prompts/sql_prompt.txt"),
        "sql_tables_user_prompt": Path("prompts/sql_tables_prompt.txt")}
        )
    
    database_schema_path: Path = Path("database/database_schema.yaml")
    database_path: Path = Path("database/ipl_analytics.duckdb")