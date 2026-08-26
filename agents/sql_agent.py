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
        self.user_deeper_analysis_prompt_path = "prompts/sql_deeper_analysis_user_prompt.txt"


    def run(self, user_question: str, database_schema: dict, previous_result:pd.DataFrame=pd.DataFrame(), required_grain:str="", required_metrics:list=[], identified_entities:list=[], validation_errors:list=[], generated_sql:str="") -> str:
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
        USER_DEEPER_ANALYSIS_PROMPT_PATH = self.user_deeper_analysis_prompt_path


        with open(SYSTEM_PROMPT_PATH, 'r') as file:
                prompt_template = file.read()

        system_prompt = prompt_template.format()

        # Load the prompt template from a text file
        with open(USER_PROMPT_PATH, 'r') as file:
            prompt_template = file.read()

        # Format the prompt with the user's question and the database schema
        user_prompt = prompt_template.format(user_question=user_question, database_schema=database_schema)

        print(f"Previous Resulttttt -- \n{previous_result}")
        print(f"{len(previous_result)}")
        if len(previous_result)>0:
            print(f"Previous result found so doing a deeper analysis.")
            # Load the prompt template from a text file
            with open(USER_DEEPER_ANALYSIS_PROMPT_PATH, 'r') as file:
                prompt_template = file.read()
    
            # Format the prompt with the user's question and the database schema
            user_prompt = prompt_template.format(user_question=user_question,database_schema=database_schema, previous_result=previous_result.to_dict(orient='records'), required_grain=required_grain, required_metrics=required_metrics,identified_entities=identified_entities)

            if validation_errors:
                print(f"Found validation errors hence appending it to the user prompt.")
                user_prompt += f"\n\nThe previously generated SQL query was invalid.\n{generated_sql}\n\nHere are the validation errors:\n{validation_errors}\nPlease generate a corrected SQL query."

            response = llm.invoke([
                # SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])

        else:
            print(f"No Previous result found so doing a normal analysis.")
            if validation_errors:
                print(f"Found validation errors hence appending it to the user prompt.")
                user_prompt += f"\n\nThe previously generated SQL query was invalid.\n{generated_sql}\n\nHere are the validation errors:\n{validation_errors}\nPlease generate a corrected SQL query."

            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
        
        sql_query = str(response.content).strip()

        return sql_query

