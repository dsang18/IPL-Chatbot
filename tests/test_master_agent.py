
import pandas as pd

from src.agents.master_agent import MasterAgent
from src.utils.sql_context_dataclass import SQLAgentContext


# Verify that the workflow starts with table selection.
def test_initial_agent_is_table_selector():
    agent = MasterAgent.__new__(MasterAgent)
    state = SQLAgentContext(user_question="Who scored the most runs?")
    assert agent._next_agent(state) == "table_selector"


# Verify that SQL generation follows table selection.
def test_sql_generator_follows_table_selection():
    agent = MasterAgent.__new__(MasterAgent)
    state = SQLAgentContext(user_question="Who scored the most runs?", selected_tables=["dim_player"])
    assert agent._next_agent(state) == "sql_generator"


# Verify that SQL execution follows SQL generation.
def test_sql_executor_follows_sql_generation():
    agent = MasterAgent.__new__(MasterAgent)
    state = SQLAgentContext(user_question="Who scored the most runs?", selected_tables=["dim_player"], generated_sql="SELECT * FROM dim_player", completed_agents=["table_selector", "sql_generator"])
    assert agent._next_agent(state) == "sql_executor"


# Verify that failed SQL execution triggers a retry.
def test_sql_execution_failure_triggers_retry():
    agent = MasterAgent.__new__(MasterAgent)
    state = SQLAgentContext(user_question="Who scored the most runs?", selected_tables=["dim_player"], generated_sql="SELECT * FROM dim_player", completed_agents=["table_selector", "sql_generator", "sql_executor"], sql_attempts=1)
    assert agent._next_agent(state) == "sql_generator"


# Verify that the workflow stops after the maximum SQL attempts.
def test_sql_execution_stops_after_maximum_attempts():
    agent = MasterAgent.__new__(MasterAgent)
    state = SQLAgentContext(user_question="Who scored the most runs?", selected_tables=["dim_player"], generated_sql="SELECT * FROM dim_player", completed_agents=["table_selector", "sql_generator", "sql_executor"], sql_attempts=3)
    assert agent._next_agent(state) == "no_data"


# Verify that KPI generation is the first analytical stage after successful SQL execution.
def test_kpi_generator_follows_successful_sql_execution():
    agent = MasterAgent.__new__(MasterAgent)
    state = SQLAgentContext(user_question="Who scored the most runs?", selected_tables=["dim_player"], generated_sql="SELECT * FROM dim_player", completed_agents=["table_selector", "sql_generator", "sql_executor"], query_result=pd.DataFrame({"player_name": ["V KOHLI"]}))
    assert agent._next_agent(state) == "kpi_generator"


# Verify that the workflow completes after all analytical agents execute.
def test_workflow_completes_after_all_agents():
    agent = MasterAgent.__new__(MasterAgent)
    state = SQLAgentContext(user_question="Who scored the most runs?", selected_tables=["dim_player"], generated_sql="SELECT * FROM dim_player", completed_agents=["table_selector", "sql_generator", "sql_executor", "kpi_generator", "insights_generator", "visualization_generator"], query_result=pd.DataFrame({"player_name": ["V KOHLI"]}))
    assert agent._next_agent(state) == "complete"
