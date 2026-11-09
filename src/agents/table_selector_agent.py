from src.utils.llm_utils import get_llm, invoke_llm, load_prompt, parse_structured_response
import json

class TableSelectorAgent:

    # Configure the table selection model.
    def __init__(self, llm_model: str = "gemini-3.5-flash-lite", model_provider: str = "google_genai", temperature: float = 0.0):
        self.llm_model = llm_model
        self.model_provider = model_provider
        self.temperature = temperature

    # Select the minimum set of tables required by the analytical plan.
    def run(self, user_question: str, query_plan: dict, metadata_schema: dict) -> list[str]:
        try:
            print("[TABLE SELECTOR] Selecting relevant tables.")

            llm = get_llm(self.llm_model, self.model_provider, self.temperature)

            user_prompt = load_prompt("./src/prompts/sql_tables_prompt.txt").format(
                user_question=user_question,
                query_plan=json.dumps(query_plan, separators=(",", ":")),
                database_schema=json.dumps(metadata_schema, separators=(",", ":"))
            )

            response = invoke_llm(
                llm,
                "You are an expert database schema selector. Return only a JSON list of table names.",
                user_prompt,
                "table_selection"
            )

            selected_tables = parse_structured_response(response, "Table Selector Agent")

            if not isinstance(selected_tables, list) or not selected_tables:
                raise ValueError("The Table Selector must return a non-empty list.")

            if not all(isinstance(table, str) for table in selected_tables):
                raise ValueError("All selected table names must be strings.")

            available_tables = set(metadata_schema["tables"])
            invalid_tables = set(selected_tables) - available_tables

            if invalid_tables:
                raise ValueError(f"Unknown tables selected: {sorted(invalid_tables)}.")

            selected_tables = list(dict.fromkeys(selected_tables))

            print(f"[TABLE SELECTOR] Selected tables: {selected_tables}.")
            return selected_tables

        except Exception as error:
            raise RuntimeError(
                f"Table selection failed for '{user_question}': {error}"
            ) from error