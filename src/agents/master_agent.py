
from collections.abc import Callable

from src.utils.sql_context_dataclass import SQLAgentContext
from src.utils.schema_loader import get_database_schema_metadata, load_custom_database_schema, load_database_schema


ProgressCallback = Callable[[str, str], None]


class MasterAgent:

    # Initialise the agents required for IPL analysis.
    def __init__(self, table_selector, sql_generator, sql_executor, insights_generator, kpi_generator, visualization_generator):
        self.table_selector = table_selector
        self.sql_generator = sql_generator
        self.sql_executor = sql_executor
        self.insights_generator = insights_generator
        self.kpi_generator = kpi_generator
        self.visualization_generator = visualization_generator

    # Execute the complete analytical workflow.
    def run(self, user_question: str, on_progress: ProgressCallback | None = None) -> SQLAgentContext:
        try:
            print("[MASTER AGENT] Starting IPL analysis.")

            # Initialize variables
            state = SQLAgentContext(user_question=user_question)
            schema = load_database_schema(state.database_schema_path)
            self._emit(on_progress, "started", "Understanding your IPL question.")

            # Start the endless loop until user ends the chat
            while True:
                next_agent = self._next_agent(state)
                state.next_agent = next_agent

                if next_agent == "complete":
                    self._emit(on_progress, "complete", "Your IPL analysis is ready.")
                    print("[MASTER AGENT] Analysis completed successfully.")
                    return state
                if next_agent == "no_data":
                    self._emit(on_progress, "no_data", "No relevant data was found after the permitted attempts.")
                    print("[MASTER AGENT] Analysis stopped because no usable data was found.")
                    return state
                
                self._emit(on_progress, next_agent, self._progress_message(next_agent))
                print(f"[MASTER AGENT] Executing agent: {next_agent}.")
                self.execute_agent(next_agent, state, schema)
                state.completed_agents.append(next_agent)

        except Exception as error:
            raise RuntimeError(f"Master Agent failed while processing '{user_question}': {error}") from error

    # Determine the next agent using deterministic workflow transitions.
    def _next_agent(self, state: SQLAgentContext) -> str:
        try:
            if not state.selected_tables:
                return "table_selector"
            if state.generated_sql.strip().lower() == "no relevant data found.":
                return "no_data"
            if not state.generated_sql:
                return "sql_generator"
            if not state.completed_agents or state.completed_agents[-1] == "sql_generator":
                return "sql_executor"
            if state.completed_agents[-1] == "sql_executor" and state.query_result.empty:
                return "sql_generator" if state.sql_attempts < state.max_sql_attempts else "no_data"
            for agent_name in ("kpi_generator", "insights_generator", "visualization_generator"):
                if agent_name not in state.completed_agents:
                    return agent_name
            return "complete"
        except Exception as error:
            raise RuntimeError(f"Unable to determine the next agent: {error}") from error

    # Execute the requested agent and update the shared analysis state.
    def execute_agent(self, agent_name: str, state: SQLAgentContext, schema: dict) -> None:
        try:
            if agent_name == "table_selector":
                state.selected_tables = self.table_selector.run(
                    state.user_question, 
                    get_database_schema_metadata(schema)
                )
            
            elif agent_name == "sql_generator":
                custom_schema = load_custom_database_schema(schema, state.selected_tables)
                state.generated_sql = self.sql_generator.run(
                    user_question=state.user_question, 
                    database_schema=custom_schema, 
                    execution_error=state.execution_error, 
                    generated_sql=state.generated_sql
                )
                state.execution_error = None
            
            elif agent_name == "sql_executor":
                state.sql_attempts += 1
                try:
                    state.query_result = self.sql_executor.run(state.generated_sql, state.selected_tables)
                    state.execution_error = "The query returned no rows." if state.query_result.empty else None
                except Exception as error:
                    state.query_result = state.query_result.iloc[0:0]
                    state.execution_error = str(error)
                    print(f"[MASTER AGENT] SQL execution attempt {state.sql_attempts} failed: {error}")
            
            elif agent_name == "kpi_generator":
                state.kpis = self.kpi_generator.run(state.user_question, state.query_result)

            elif agent_name == "insights_generator":
                state.insights = self.insights_generator.run(state.user_question, state.query_result)

            elif agent_name == "visualization_generator":
                state.visualizations = self.visualization_generator.run(
                    state.user_question, 
                    state.query_result
                )
            
            else:
                raise ValueError(f"Unknown agent: {agent_name}.")
        except Exception as error:
            raise RuntimeError(f"Agent '{agent_name}' failed: {error}") from error

    # Send progress updates to the API when a callback is available.
    @staticmethod
    def _emit(callback: ProgressCallback | None, stage: str, message: str) -> None:
        try:
            if callback:
                callback(stage, message)
        except Exception as error:
            print(f"[MASTER AGENT] Progress callback failed: {error}")

    # Return the user-facing progress message for each agent.
    @staticmethod
    def _progress_message(agent_name: str) -> str:
        try:
            return {
                "table_selector": "Selecting the relevant IPL data tables.",
                "sql_generator": "Preparing the statistical analysis.",
                "sql_executor": "Querying the IPL database.",
                "kpi_generator": "Selecting the key performance indicators.",
                "insights_generator": "Generating statistical insights.",
                "visualization_generator": "Planning the most useful visualization.",
            }[agent_name]
        except Exception as error:
            raise ValueError(f"No progress message is configured for agent '{agent_name}': {error}") from error
