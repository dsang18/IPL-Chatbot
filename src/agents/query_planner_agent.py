
import json

from src.utils.llm_utils import get_llm, invoke_llm, load_prompt, parse_structured_response


# Validate analytical steps and their dependencies before execution.
def validate_analytical_plan(query_plan: dict, max_steps: int = 4) -> dict:
    try:
        steps = query_plan.get("steps", [])
        execution_mode = query_plan.get("execution_mode", "single")

        if execution_mode not in ("single", "multi"):
            raise ValueError("'execution_mode' must be 'single' or 'multi'.")
        if not isinstance(steps, list):
            raise ValueError("'steps' must be a list.")
        if not steps and query_plan["answerable"]:
            steps = [{"step_id": "step_1", "objective": query_plan["intent"], "depends_on": [], "required_outputs": [], "uses_intermediate_results": False}]
        if len(steps) > max_steps:
            raise ValueError(f"Analytical plan contains {len(steps)} steps. Maximum allowed is {max_steps}.")
        if execution_mode == "multi" and len(steps) < 2:
            raise ValueError("A multi-step plan must contain at least two steps.")
        if execution_mode == "single" and len(steps) > 1:
            raise ValueError("A single-step plan cannot contain multiple steps.")

        step_ids = [step.get("step_id") for step in steps]
        if any(not isinstance(step_id, str) or not step_id.strip() for step_id in step_ids):
            raise ValueError("Every analytical step must have a non-empty string step_id.")
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("Analytical step IDs must be unique.")

        step_map = {step["step_id"]: step for step in steps}
        for step in steps:
            required_fields = {"objective", "depends_on", "required_outputs", "uses_intermediate_results"}
            missing_fields = required_fields - set(step)
            if missing_fields:
                raise ValueError(f"Step '{step['step_id']}' is missing fields: {sorted(missing_fields)}.")
            if not isinstance(step["objective"], str) or not step["objective"].strip():
                raise ValueError(f"Step '{step['step_id']}' must have a non-empty objective.")
            if not isinstance(step["depends_on"], list) or not all(isinstance(item, str) for item in step["depends_on"]):
                raise ValueError(f"Step '{step['step_id']}' depends_on must be a list of step IDs.")
            if not isinstance(step["required_outputs"], list):
                raise ValueError(f"Step '{step['step_id']}' required_outputs must be a list.")
            if not isinstance(step["uses_intermediate_results"], bool):
                raise ValueError(f"Step '{step['step_id']}' uses_intermediate_results must be a boolean.")
            if step["step_id"] in step["depends_on"]:
                raise ValueError(f"Step '{step['step_id']}' cannot depend on itself.")
            unknown_dependencies = set(step["depends_on"]) - set(step_ids)
            if unknown_dependencies:
                raise ValueError(f"Step '{step['step_id']}' contains unknown dependencies: {sorted(unknown_dependencies)}.")
            if step["depends_on"] and not step["uses_intermediate_results"]:
                raise ValueError(f"Step '{step['step_id']}' has dependencies but uses_intermediate_results is false.")

        # Detect circular dependencies using depth-first traversal.
        visited = set()
        active = set()

        def visit(step_id: str) -> None:
            if step_id in active:
                raise ValueError(f"Circular dependency detected at step '{step_id}'.")
            if step_id in visited:
                return
            active.add(step_id)
            for dependency in step_map[step_id]["depends_on"]:
                visit(dependency)
            active.remove(step_id)
            visited.add(step_id)

        for step_id in step_ids:
            visit(step_id)

        # Ensure every dependency appears before the step that uses it.
        positions = {step_id: index for index, step_id in enumerate(step_ids)}
        for step in steps:
            for dependency in step["depends_on"]:
                if positions[dependency] >= positions[step["step_id"]]:
                    raise ValueError(f"Dependency '{dependency}' must appear before step '{step['step_id']}'.")

        query_plan["execution_mode"] = execution_mode
        query_plan["steps"] = steps
        print(f"[QUERY PLANNER] Validated {len(steps)} analytical step(s) in '{execution_mode}' mode.")
        return query_plan
    except Exception as error:
        raise ValueError(f"Analytical plan validation failed: {error}") from error


# Configure the query planning model.
class QueryPlannerAgent:

    # Configure the query planning model.
    def __init__(self, llm_model: str = "gemini-3.5-flash-lite", model_provider: str = "google_genai", temperature: float = 0.0):
        self.llm_model = llm_model
        self.model_provider = model_provider
        self.temperature = temperature

    # Convert the user's question and context into a structured analytical plan.
    def run(self, user_question: str, metadata_schema: dict, conversation_context: dict | None = None, max_steps: int = 4) -> dict:
        try:
            print("[QUERY PLANNER] Creating analytical execution plan.")

            llm = get_llm(self.llm_model, self.model_provider)
            system_prompt = load_prompt("./src/prompts/query_planner_system_prompt.txt")
            user_prompt = load_prompt("./src/prompts/query_planner_user_prompt.txt").format(user_question=user_question, database_schema=json.dumps(metadata_schema, separators=(",", ":")), conversation_context=json.dumps(conversation_context or {}, separators=(",", ":")))

            print(f"[QUERY PLANNER] Prompt size: {len(user_prompt)} characters.")
            response = invoke_llm(llm, system_prompt, user_prompt, "query_planning")
            query_plan = parse_structured_response(response, "Query Planner Agent")

            required_fields = {"answerable", "reason", "intent", "entities", "metrics", "filters", "group_by", "order_by", "limit", "grain"}
            if not isinstance(query_plan, dict):
                raise ValueError("Query Planner must return a JSON object.")

            missing_fields = required_fields - set(query_plan)
            if missing_fields:
                raise ValueError(f"Query plan is missing fields: {sorted(missing_fields)}.")
            if not isinstance(query_plan["answerable"], bool):
                raise ValueError("'answerable' must be a boolean.")
            for field in ("entities", "metrics", "filters", "group_by", "order_by"):
                if not isinstance(query_plan[field], list):
                    raise ValueError(f"Query plan field '{field}' must be a list.")
            if query_plan["limit"] is not None and (not isinstance(query_plan["limit"], int) or query_plan["limit"] < 1):
                raise ValueError("Query plan limit must be a positive integer or null.")
            if not isinstance(query_plan["intent"], str) or not query_plan["intent"].strip():
                raise ValueError("Query plan intent cannot be empty.")
            if not isinstance(max_steps, int) or max_steps < 1:
                raise ValueError("'max_steps' must be a positive integer.")

            query_plan = validate_analytical_plan(query_plan, max_steps)

            print(f"[QUERY PLANNER] Intent identified: {query_plan['intent']}.")
            print(f"[QUERY PLANNER] Execution mode: {query_plan['execution_mode']}.")
            for step in query_plan["steps"]:
                print(f"[QUERY PLANNER] {step['step_id']}: {step['objective']} | Dependencies: {step['depends_on']}")
            return query_plan
        except Exception as error:
            raise RuntimeError(f"Query planning failed for '{user_question}': {error}") from error
