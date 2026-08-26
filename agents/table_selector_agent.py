from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
import ast


class TableSelectorAgent:

    def __init__(self, llm_model: str = "openai/gpt-oss-120b", model_provider: str = "groq", temperature: float = 0.2):
        self.llm_model = llm_model
        self.model_provider = model_provider
        self.temperature = temperature
        self.user_prompt = "prompts/sql_tables_prompt.txt"
    
    def run(self, user_question:str, metadata_schema:dict) -> list[str]:
        """
        Decide which tables to use based on the database schema.

        Returns:
            list: A list of table names to be used in SQL generation.
        """

        # Initalize the LLM with llama model
        llm = init_chat_model(
            model=self.llm_model,
            model_provider=self.model_provider,
            temperature=self.temperature
        )

        SQL_SCHEMA_PROMPT_PATH = self.user_prompt

        with open(SQL_SCHEMA_PROMPT_PATH, 'r') as file:
            prompt_template = file.read()

        prompt = prompt_template.format(user_question=user_question, database_schema=metadata_schema)

        response = llm.invoke(
            input=[
                HumanMessage(content=prompt)
            ],
        )
        
        selected_tables = ast.literal_eval(str(response.content).strip())

        return selected_tables

