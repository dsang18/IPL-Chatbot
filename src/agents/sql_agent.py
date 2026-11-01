
from src.utils.llm_utils import get_llm, invoke_llm, load_prompt


class SQLAgent:

    # Configure the SQL generation model.
    def __init__(self, llm_model: str = "openai/gpt-oss-120b", model_provider: str = "groq", temperature: float = 0.0):
        self.llm_model = llm_model
        self.model_provider = model_provider
        self.temperature = temperature

    # Generate SQL using the user's question and the selected database schema.
    def run(self, user_question: str, database_schema: dict, execution_error: str | None = None, generated_sql: str = "") -> str:
        try:
            print("[SQL AGENT] Generating SQL.")

            # Initialize LLM variables
            llm = get_llm(self.llm_model, self.model_provider, self.temperature)
            system_prompt = load_prompt("./src/prompts/sql_system_prompt.txt")
            user_prompt = load_prompt("./src/prompts/sql_prompt.txt").format(user_question=user_question, database_schema=database_schema)

            # Check if this is the second time we are trying to ask for the sql query after an error
            if execution_error:
                user_prompt += f"\n\nPrevious SQL:\n{generated_sql}\nExecution outcome:\n{execution_error}\nGenerate a corrected query."

            # Invoke the llm agent to generate an sql query
            sql_query = invoke_llm(llm, system_prompt, user_prompt, "sql_generation").strip()
            sql_query = sql_query.removeprefix("```sql").removesuffix("```").strip()

            # Check if sql query is found in the LLM response
            if sql_query.lower().rstrip(".;") == "no relevant data found":
                return "No relevant data found."
            
            # Check if the SQL Query ends with a ';' (semicolon)
            if not sql_query.endswith(";"):
                sql_query += ";"

            return sql_query

        except Exception as error:
            raise RuntimeError(f"SQL Agent failed to generate a query for '{user_question}': {error}") from error
