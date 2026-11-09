from src.utils.llm_utils import get_llm, invoke_llm, load_prompt, parse_structured_response
import json

class QueryPlannerAgent:

    # Configure the query planning model.
    def __init__(self, llm_model: str = "gemini-3.5-flash-lite", model_provider: str = "google_genai", temperature: float = 0.0):
        self.llm_model = llm_model
        self.model_provider = model_provider
        # self.temperature = temperature

    # Convert the user's question into a structured analytical plan.
    def run(self, user_question: str, metadata_schema: dict) -> dict:
        try:
            print("[QUERY PLANNER] Creating analytical query plan.")

            llm = get_llm(self.llm_model, self.model_provider)

            system_prompt = load_prompt("./src/prompts/query_planner_system_prompt.txt")
            user_prompt = load_prompt("./src/prompts/query_planner_user_prompt.txt").format(
                user_question=user_question,
                database_schema=json.dumps(metadata_schema, separators=(",", ":"))
            )

            print(f"[QUERY PLANNER] Prompt size: {len(user_prompt)} characters.")

            response = invoke_llm(
                llm, system_prompt, user_prompt, "query_planning"
            )

            query_plan = parse_structured_response(response, "Query Planner Agent")

            required_fields = {
                "answerable", "reason", "intent", "entities", "metrics",
                "filters", "group_by", "order_by", "limit", "grain"
            }

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

            if query_plan["limit"] is not None:
                if not isinstance(query_plan["limit"], int) or query_plan["limit"] < 1:
                    raise ValueError("Query plan limit must be a positive integer or null.")

            if not isinstance(query_plan["intent"], str) or not query_plan["intent"].strip():
                raise ValueError("Query plan intent cannot be empty.")

            print(f"[QUERY PLANNER] Intent identified: {query_plan['intent']}.")

            for key,value in query_plan.items():
                print(f"• {key} ➜ {value}")
                
            return query_plan

        except Exception as error:
            raise RuntimeError(
                f"Query planning failed for '{user_question}': {error}"
            ) from error