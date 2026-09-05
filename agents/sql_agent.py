import os
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage
import pandas as pd

load_dotenv()

os.environ["GROQ_API_KEY"] = str(os.getenv("GROQ_API_KEY"))


class SQLAgent:

    def __init__(self, llm_model: str = "openai/gpt-oss-120b", model_provider: str = "groq", temperature: float = 1):
        self.llm_model = llm_model
        self.model_provider = model_provider
        self.temperature = temperature
        self.system_prompt_path = "prompts/sql_system_prompt.txt"
        self.user_prompt_path = "prompts/sql_prompt.txt"


    def run(self, user_question: str, database_schema: dict, execution_error: str | None = None, generated_sql: str = "") -> str:
        """
        Generate SQL query based on the user's question.

        Args:
            user_question (str): The user's question for which to generate an SQL query.

        Returns:
            str: The generated SQL query.
        """

        # Initalize the LLM with llama model
        llm = init_chat_model(
            model=self.llm_model,
            model_provider=self.model_provider,
            temperature=self.temperature
        )

        SYSTEM_PROMPT_PATH = self.system_prompt_path
        USER_PROMPT_PATH = self.user_prompt_path


        with open(SYSTEM_PROMPT_PATH, 'r') as file:
                prompt_template = file.read()

        system_prompt = prompt_template.format()

        # Load the prompt template from a text file
        with open(USER_PROMPT_PATH, 'r') as file:
            prompt_template = file.read()

        # Format the prompt with the user's question and the database schema
        user_prompt = prompt_template.format(user_question=user_question, database_schema=database_schema)

        if execution_error:
            user_prompt += (
                "\n\nThe previous SQL query did not produce a usable result."
                f"\nPrevious SQL:\n{generated_sql}"
                f"\nExecution outcome:\n{execution_error}"
                "\nGenerate a corrected SQL query."
            )

        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        sql_query = str(response.content).strip()

        return sql_query

