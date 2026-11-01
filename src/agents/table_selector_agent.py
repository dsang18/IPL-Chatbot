
from src.utils.llm_utils import get_llm, invoke_llm, load_prompt, parse_structured_response


class TableSelectorAgent:

    # Configure the table selection model.
    def __init__(self, llm_model: str = "openai/gpt-oss-120b", model_provider: str = "groq", temperature: float = 0.2):
        self.llm_model = llm_model
        self.model_provider = model_provider
        self.temperature = temperature

    # Select relevant database tables using the available schema metadata.
    def run(self, user_question: str, metadata_schema: dict) -> list[str]:
        try:
            print("[TABLE SELECTOR] Selecting relevant tables.")
            
            # Initialize LLM variables
            llm = get_llm(self.llm_model, self.model_provider, self.temperature)
            user_prompt = load_prompt("./src/prompts/sql_tables_prompt.txt").format(
                user_question=user_question, 
                database_schema=metadata_schema
            )

            # Invoke LLM to return tables required to answer the query
            response = invoke_llm(
                llm, "Return only a list of valid table names.", user_prompt, "table_selection")
            selected_tables = parse_structured_response(response, "Table Selector Agent")

            # Check if the response return is a list with values
            if not isinstance(selected_tables, list) or not selected_tables:
                raise ValueError("The Table Selector must return a non-empty list.")
            
            # Check if there are any tables that are not in our database
            invalid_tables = set(selected_tables) - set(metadata_schema)
            if invalid_tables:
                raise ValueError(f"The Table Selector returned unknown tables: {sorted(invalid_tables)}.")
            
            selected_tables = list(dict.fromkeys(selected_tables))
            print(f"[TABLE SELECTOR] Selected tables: {selected_tables}.")
            return selected_tables
        
        except Exception as error:
            raise RuntimeError(
                f"Table selection failed for question '{user_question}': {error}"
            ) from error
