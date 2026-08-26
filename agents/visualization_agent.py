import json
import pandas as pd

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()


class VisualizationGenerator:

    def __init__(self,llm_model: str = "openai/gpt-oss-120b",model_provider: str = "groq",temperature: float = 0):
        self.llm_model = llm_model
        self.model_provider = model_provider
        self.temperature = temperature
        self.system_prompt_path = ("prompts/sql_visualization_system_prompt.txt")
        self.user_prompt_path = ("prompts/sql_visualization_user_prompt.txt")

    def run(self,user_question: str,query_result: pd.DataFrame) -> dict:

        llm = init_chat_model(
            model=self.llm_model,
            model_provider=self.model_provider,
            temperature=self.temperature
        )

        with open(self.system_prompt_path, "r") as file:
            system_prompt = file.read()

        result_text = query_result.to_string(index=False)

        with open(self.system_prompt_path, "r") as file:
            system_prompt = file.read()
        
        with open(self.user_prompt_path, "r") as file:
            user_prompt = file.read()

        user_prompt = user_prompt.format(query_result=result_text, result_columns=list(query_result.columns))

        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])

        response_text = str(response.content).strip()

        try:
            visualization = json.loads(response_text)
        except json.JSONDecodeError:
            raise ValueError(
                f"Visualization Agent returned invalid JSON:\n"
                f"{response_text}"
            )

        return visualization