import pandas as pd
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage
import json

class DeeperAnalysisChecker:

    def __init__(self, llm_model: str = "openai/gpt-oss-120b", model_provider: str = "groq", temperature: float = 0):
        self.llm_model = llm_model
        self.model_provider = model_provider
        self.temperature = temperature
        self.system_prompt_path = ("prompts/sql_deeper_analysis_system_prompt.txt")


    def run(self,user_question: str,query_result: pd.DataFrame) -> dict:

        llm = init_chat_model(
            model=self.llm_model,
            model_provider=self.model_provider,
            temperature=self.temperature
        )

        with open(self.system_prompt_path, "r") as file:
            system_prompt = file.read()

        result_text = query_result.to_string(index=False)

        user_prompt = f"""
Original User Question:
{user_question}

Current SQL Query Result:
{result_text}

Analyze whether this result is sufficient to answer the user's question
at a detailed statistical level.

If deeper analysis is required, identify the entity/entities and the
appropriate grain and metrics required to provide the deeper analysis.
"""

        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])

        response_text = str(response.content).strip()

        try:
            decision = json.loads(response_text)
        except json.JSONDecodeError:
            raise ValueError(
                f"Deeper Analysis Agent returned invalid JSON:\n{response_text}"
            )

        return decision

