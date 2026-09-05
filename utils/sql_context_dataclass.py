from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
import pandas as pd

@dataclass
class SQLAgentContext:

    user_question: str

    # Database / SQL
    selected_tables: list[str] = field(default_factory=list)
    generated_sql: str = field(default_factory=str)
    execution_error: Optional[str] = None
    query_result: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Final Outputs
    insights: Optional[str] = None
    kpis: Optional[dict] = None
    visualizations: Optional[dict] = None

    # Orchestration
    next_agent: str = ""
    completed_agents: list = field(default_factory=list)
    sql_attempts: int = 0
    max_sql_attempts: int = 3

    # Paths to the database schema and database file
    database_schema_path: Path = Path("database/database_schema.yaml")
    database_path: Path = Path("database/ipl_analytics.duckdb")
