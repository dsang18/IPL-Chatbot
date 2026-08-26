from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage
import pandas as pd
import ast

class InsightGenerator:

    def __init__(self, llm_model: str = "openai/gpt-oss-120b", model_provider: str = "groq", temperature: float = 1):
        self.llm_model = llm_model
        self.model_provider = model_provider
        self.temperature = temperature
        self.system_prompt_path = ("prompts/sql_insights_system_prompt.txt")
        self.user_prompt_path = ("prompts/sql_insights_user_prompt.txt")


    def run(self, user_question: str, query_result: pd.DataFrame) -> str:

        llm = init_chat_model(
            model=self.llm_model,
            model_provider=self.model_provider,
            temperature=self.temperature
        )

        with open(self.system_prompt_path, "r") as file:
            system_prompt = file.read()

        with open(self.user_prompt_path, "r") as file:
            user_prompt = file.read()

        result_text = query_result.to_string(index=False)
        user_prompt = user_prompt.format(user_question=user_question, query_result=result_text)

        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])

        return ast.literal_eval(str(response.content).strip())