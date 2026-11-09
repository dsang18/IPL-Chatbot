import pandas as pd

from src.agents.master_agent import MasterAgent
from src.utils.sql_context_dataclass import SQLAgentContext


# Create a MasterAgent instance for testing workflow transitions.
def create_test_agent() -> MasterAgent:
    try:
        return MasterAgent.__new__(MasterAgent)
    except Exception as error:
        raise RuntimeError(f"Unable to create test MasterAgent: {error}") from error


# Create a query-ready state for workflow tests.
def create_query_state() -> SQLAgentContext:
    try:
        return SQLAgentContext(
            user_question="Who scored the most runs?",
            query_plan={"answerable": True},
            selected_tables=["dim_player"],
            completed_agents=["query_planner", "table_selector"]
        )
    except Exception as error:
        raise RuntimeError(f"Unable to create test query state: {error}") from error

        
# Verify that the workflow starts with query planning.
def test_initial_agent_is_query_planner():
    agent = create_test_agent()
    state = SQLAgentContext(user_question="Who scored the most runs?")

    assert agent._next_agent(state) == "query_planner"


# Verify that table selection follows query planning.
def test_table_selector_follows_query_planner():
    agent = create_test_agent()
    state = SQLAgentContext(
        user_question="Who scored the most runs?",
        query_plan={"answerable": True},
        completed_agents=["query_planner"]
    )

    assert agent._next_agent(state) == "table_selector"


# Verify that unanswerable questions stop after planning.
def test_unanswerable_question_stops_workflow():
    agent = create_test_agent()
    state = SQLAgentContext(
        user_question="What is the weather today?",
        query_plan={"answerable": False},
        completed_agents=["query_planner"]
    )

    assert agent._next_agent(state) == "no_data"


# Verify that SQL generation follows table selection.
def test_sql_generator_follows_table_selection():
    agent = create_test_agent()
    state = create_query_state()

    assert agent._next_agent(state) == "sql_generator"


# Verify that SQL execution follows SQL generation.
def test_sql_executor_follows_sql_generation():
    agent = create_test_agent()
    state = create_query_state()
    state.completed_agents.append("sql_generator")

    assert agent._next_agent(state) == "sql_executor"


# Verify that execution errors trigger SQL regeneration.
def test_sql_execution_failure_triggers_retry():
    agent = create_test_agent()
    state = create_query_state()
    state.completed_agents.extend(["sql_generator", "sql_executor"])
    state.execution_error = "Binder Error: Column not found."
    state.sql_attempts = 1

    assert agent._next_agent(state) == "sql_generator"


# Verify that successful empty results do not trigger retries.
def test_successful_empty_result_stops_workflow():
    agent = create_test_agent()
    state = create_query_state()
    state.completed_agents.extend(["sql_generator", "sql_executor"])
    state.execution_error = None
    state.sql_attempts = 1

    assert agent._next_agent(state) == "no_data"


# Verify that failed SQL execution stops after maximum attempts.
def test_sql_execution_stops_after_maximum_attempts():
    agent = create_test_agent()
    state = create_query_state()
    state.completed_agents.extend(["sql_generator", "sql_executor"])
    state.execution_error = "SQL execution failed."
    state.sql_attempts = 3

    assert agent._next_agent(state) == "no_data"


# Verify that KPI generation follows successful SQL execution.
def test_kpi_generator_follows_successful_sql_execution():
    agent = create_test_agent()
    state = create_query_state()
    state.completed_agents.extend(["sql_generator", "sql_executor"])
    state.query_result = pd.DataFrame({"player_name": ["V KOHLI"]})

    assert agent._next_agent(state) == "kpi_generator"


# Verify that the workflow completes after all analytical agents execute.
def test_workflow_completes_after_all_agents():
    agent = create_test_agent()
    state = create_query_state()

    state.completed_agents.extend([
        "sql_generator",
        "sql_executor",
        "kpi_generator",
        "insights_generator",
        "visualization_generator"
    ])

    state.query_result = pd.DataFrame({"player_name": ["V KOHLI"]})

    assert agent._next_agent(state) == "complete"