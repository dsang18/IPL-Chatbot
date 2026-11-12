
from collections.abc import Callable
import json

import pandas as pd

from src.utils.sql_context_dataclass import SQLAgentContext
from src.utils.schema_loader import get_query_planner_schema, load_custom_database_schema, load_database_schema


ProgressCallback = Callable[[str, str], None]


class MasterAgent:

    # Initialise the agents required for IPL analysis.
    def __init__(self, query_planner, sql_generator, sql_executor, insights_generator, kpi_generator, visualization_generator, result_synthesizer=None):
        self.query_planner = query_planner
        self.sql_generator = sql_generator
        self.sql_executor = sql_executor
        self.insights_generator = insights_generator
        self.kpi_generator = kpi_generator
        self.visualization_generator = visualization_generator
        self.result_synthesizer = result_synthesizer

    # Execute the complete single-step or multi-step analytical workflow.
    def run(self, user_question: str, on_progress: ProgressCallback | None = None, conversation_context: dict | None = None) -> SQLAgentContext:
        try:
            print("[MASTER AGENT] Starting IPL analysis.")
            state = SQLAgentContext(user_question=user_question, conversation_context=conversation_context or {})
            schema = load_database_schema(state.database_schema_path)
            self._emit(on_progress, "started", "Understanding your IPL question.")

            metadata_schema = get_query_planner_schema(schema)
            state.query_plan = self.query_planner.run(user_question, metadata_schema, state.conversation_context, state.max_analytical_steps)
            state.analytical_plan = state.query_plan
            state.analytical_steps = state.query_plan.get("steps", [])
            state.selected_tables = state.query_plan.get("entities", [])

            if not state.query_plan["answerable"]:
                state.next_agent = "no_data"
                self._emit(on_progress, "no_data", state.query_plan.get("reason", "Question cannot be answered."))
                return state

            if state.query_plan.get("execution_mode", "single") == "multi":
                self._execute_multi_step_plan(state, schema, on_progress)
            else:
                step = state.analytical_steps[0]
                self._execute_analytical_step(state, step, schema, on_progress)
                state.query_result = state.step_results.get(step["step_id"], pd.DataFrame())

            if state.execution_error or state.query_result.empty:
                state.next_agent = "no_data"
                self._emit(on_progress, "no_data", "The analysis did not produce usable results.")
                return state

            if state.query_plan.get("execution_mode") == "multi" and self.result_synthesizer:
                self._emit(on_progress, "result_synthesis", "Combining the results from each analytical step.")
                synthesis = self.result_synthesizer.run(state.user_question, state.analytical_plan, state.execution_trace)
                state.insights = synthesis["insights"]
                state.domain_analytics["synthesis_summary"] = synthesis["summary"]

            self._generate_final_outputs(state, on_progress)
            state.next_agent = "complete"
            self._emit(on_progress, "complete", "Your IPL analysis is ready.")
            print("[MASTER AGENT] Analysis completed successfully.")
            return state

        except Exception as error:
            raise RuntimeError(f"Master Agent failed while processing '{user_question}': {error}") from error

    # Execute analytical steps sequentially while preserving their intermediate results.
    def _execute_multi_step_plan(self, state: SQLAgentContext, schema: dict, on_progress: ProgressCallback | None) -> None:
        try:
            print(f"[MASTER AGENT] Executing {len(state.analytical_steps)} analytical steps.")
            for step in state.analytical_steps:
                step_id = step["step_id"]
                self._emit(on_progress, "analytical_step", f"Executing step {step_id}: {step['objective']}")
                self._execute_analytical_step(state, step, schema, on_progress)
                if state.execution_error:
                    raise RuntimeError(f"Analytical step '{step_id}' failed: {state.execution_error}")
            state.query_result = self._combine_step_results(state)
        except Exception as error:
            state.execution_error = str(error)
            raise RuntimeError(f"Multi-step analytical execution failed: {error}") from error

    # Generate and execute SQL for one analytical step with bounded retries.
    def _execute_analytical_step(self, state: SQLAgentContext, step: dict, schema: dict, on_progress: ProgressCallback | None) -> None:
        try:
            step_id = step["step_id"]
            state.current_step_id = step_id
            dependencies = step.get("depends_on", [])
            intermediate_results = {dependency: state.step_results[dependency].head(50).to_dict(orient="records") for dependency in dependencies if dependency in state.step_results}

            if len(intermediate_results) != len(dependencies):
                raise ValueError(f"Required intermediate results are missing for step '{step_id}'.")

            step_question = f"Original question: {state.user_question}\nAnalytical step: {step['objective']}\nRequired outputs: {step.get('required_outputs', [])}"
            step_plan = {**state.query_plan, "intent": step["objective"], "step": step, "execution_mode": "single"}

            for attempt in range(1, state.max_sql_attempts_per_step + 1):
                print(f"[MASTER AGENT] Step {step_id}, SQL attempt {attempt}.")
                custom_schema = load_custom_database_schema(schema, state.selected_tables)
                generated_sql = self.sql_generator.run(user_question=step_question, query_plan=step_plan, database_schema=custom_schema, execution_error=state.execution_error, generated_sql=state.generated_sql, intermediate_results=intermediate_results)
                state.generated_sql = generated_sql
                state.sql_attempts = attempt
                self._emit(on_progress, "sql_execution", f"Running analytical step {step_id}, attempt {attempt}.")
                try:
                    result = self.sql_executor.run(generated_sql, state.selected_tables, custom_schema)
                    if result.empty:
                        raise ValueError(f"Step '{step_id}' returned no rows.")
                    state.step_results[step_id] = result
                    state.execution_error = None
                    state.execution_trace.append({"step_id": step_id, "objective": step["objective"], "status": "completed", "sql": generated_sql, "row_count": len(result), "columns": result.columns.tolist(), "depends_on": dependencies, "result_preview": result.head(10).to_dict(orient="records")})
                    print(f"[MASTER AGENT] Step {step_id} completed. Rows: {len(result)}.")
                    return
                except Exception as error:
                    state.execution_error = str(error)
                    state.execution_trace.append({"step_id": step_id, "objective": step["objective"], "status": "retrying" if attempt < state.max_sql_attempts_per_step else "failed", "sql": generated_sql, "error": str(error), "attempt": attempt, "depends_on": dependencies})
                    print(f"[MASTER AGENT] Step {step_id} attempt {attempt} failed: {error}")

            raise RuntimeError(f"Step '{step_id}' exhausted {state.max_sql_attempts_per_step} SQL attempts: {state.execution_error}")
        except Exception as error:
            raise RuntimeError(f"Unable to execute analytical step '{step.get('step_id', 'unknown')}': {error}") from error

    # Combine step outputs into one traceable result dataset.
    @staticmethod
    def _combine_step_results(state: SQLAgentContext) -> pd.DataFrame:
        try:
            if not state.step_results:
                return pd.DataFrame()
            final_step_id = state.analytical_steps[-1]["step_id"]
            return state.step_results[final_step_id].copy()
        except Exception as error:
            raise RuntimeError(f"Unable to select the final analytical result: {error}") from error

    # Generate KPIs, insights and visualizations from the final analytical result.
    def _generate_final_outputs(self, state: SQLAgentContext, on_progress: ProgressCallback | None) -> None:
        try:
            if not state.insights:
                self._emit(on_progress, "insights_generator", "Generating statistical insights.")
                state.insights = self.insights_generator.run(state.user_question, state.query_result)
            self._emit(on_progress, "kpi_generator", "Selecting key performance indicators.")
            state.kpis = self.kpi_generator.run(state.user_question, state.query_result)
            self._emit(on_progress, "visualization_generator", "Preparing visualizations.")
            state.visualizations = self.visualization_generator.run(state.user_question, state.query_result)
            state.domain_analytics["execution_trace"] = state.execution_trace
            state.domain_analytics["execution_mode"] = state.query_plan.get("execution_mode", "single")
        except Exception as error:
            raise RuntimeError(f"Final analytical output generation failed: {error}") from error

    # Send progress updates when a callback is available.
    @staticmethod
    def _emit(callback: ProgressCallback | None, stage: str, message: str) -> None:
        try:
            if callback:
                callback(stage, message)
        except Exception as error:
            print(f"[MASTER AGENT] Progress callback failed: {error}")
