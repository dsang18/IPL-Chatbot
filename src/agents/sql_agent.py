from src.utils.llm_utils import get_llm, invoke_llm, load_prompt
import json

class SQLAgent:

    # Configure the SQL generation model.
    def __init__(self, llm_model: str = "gemini-3.5-flash-lite", model_provider: str = "google_genai", temperature: float = 0.0):
        self.llm_model = llm_model
        self.model_provider = model_provider
        self.temperature = temperature

    # Generate SQL using the structured query plan and selected database schema.
    def run(self, user_question: str, query_plan: dict, database_schema: dict, execution_error: str | None = None, generated_sql: str = "") -> str:
        try:
            print("[SQL AGENT] Generating SQL.")

            llm = get_llm(self.llm_model, self.model_provider, self.temperature)

            system_prompt = load_prompt("./src/prompts/sql_system_prompt.txt")

            user_prompt = load_prompt("./src/prompts/sql_prompt.txt").format(
                user_question=user_question,
                query_plan=json.dumps(query_plan, separators=(",", ":")),
                database_schema=json.dumps(database_schema, separators=(",", ":")),
                execution_error=execution_error or "None",
                generated_sql=generated_sql or "None"
            )

            sql_query = invoke_llm(
                llm, system_prompt, user_prompt, "sql_generation"
            ).strip()

            sql_query = sql_query.removeprefix("```sql").removesuffix("```").strip()

            if sql_query.lower().rstrip(".;") == "no relevant data found":
                return "No relevant data found."

            if not sql_query.endswith(";"):
                sql_query += ";"

            print("[SQL AGENT] SQL generation completed.")
            return sql_query

        except Exception as error:
            raise RuntimeError(
                f"SQL generation failed for '{user_question}': {error}"
            ) from error