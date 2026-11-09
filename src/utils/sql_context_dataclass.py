
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]


@dataclass
class SQLAgentContext:
    user_question: str
    conversation_context: dict[str, Any] = field(default_factory=dict)
    query_plan: dict[str, Any] = field(default_factory=dict)
    selected_tables: list[str] = field(default_factory=list)
    generated_sql: str = ""
    execution_error: str | None = None
    query_result: pd.DataFrame = field(default_factory=pd.DataFrame)
    insights: list[str] = field(default_factory=list)
    kpis: dict[str, Any] = field(default_factory=dict)
    visualizations: list[dict[str, Any]] = field(default_factory=list)
    domain_analytics: dict[str, Any] = field(default_factory=dict)
    next_agent: str = ""
    completed_agents: list[str] = field(default_factory=list)
    sql_attempts: int = 0
    max_sql_attempts: int = 3
    database_schema_path: Path = ROOT_DIR / "database" / "database_schema.yaml"
    database_path: Path = ROOT_DIR / "database" / "ipl_analytics.duckdb"
