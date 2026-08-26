from dataclasses import dataclass, field
from typing import Optional, Any
from pathlib import Path
import pandas as pd

@dataclass
class SQLAgentContext:

    user_question: str

    # Database / SQL
    selected_tables: list[str] = field(default_factory=list)
    generated_sql: str = field(default_factory=str)
    validation_errors: list[str] = field(default_factory=list)
    query_result: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Analysis
    requires_deeper_analysis: bool = False
    identified_entities: list[dict] = field(default_factory=list)
    required_grain: str = ""
    required_metrics: list[str] = field(default_factory=list)

    # Final Outputs
    insights: Optional[str] = None
    kpis: Optional[dict] = None
    visualizations: Optional[dict] = None

    # Orchestration
    next_agent: str = ""
    completed_agents: list = field(default_factory=list)
    # LLM Call Limits
    iteration: int = 0
    max_iterations: int = 10

    # Paths to the database schema and database file
    database_schema_path: Path = Path("database/database_schema.yaml")
    database_path: Path = Path("database/ipl_analytics.duckdb")