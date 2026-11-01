
import pandas as pd
from src.utils.llm_utils import get_llm, invoke_llm, load_prompt, parse_structured_response


class InsightGenerator:

    # Configure the statistical insight generation model.
    def __init__(self, llm_model: str = "openai/gpt-oss-120b", model_provider: str = "groq", temperature: float = 0.2):
        self.llm_model = llm_model
        self.model_provider = model_provider
        self.temperature = temperature

    # Generate concise statistical observations from the analytical dataset.
    def run(self, user_question: str, query_result: pd.DataFrame) -> list[str]:
        try:
            print("[INSIGHTS AGENT] Generating statistical insights.")

            # Check if the sql query result is empty
            if query_result.empty:
                raise ValueError("Cannot generate insights from an empty dataset.")

            # Initialize LLM variables
            llm = get_llm(self.llm_model, self.model_provider, self.temperature)
            system_prompt = load_prompt(f"./src/prompts/sql_insights_system_prompt.txt")
            user_prompt = load_prompt(f"./src/prompts/sql_insights_user_prompt.txt").format(
                user_question=user_question, 
                query_result=query_result.head(200).to_string(index=False)
            )
            
            # Invoke LLM to generate AI insights 
            response = invoke_llm(llm, system_prompt, user_prompt, "insight_generation")
            insights = parse_structured_response(response, "Insights Agent")

            # Check if insights is a list of strings
            if not isinstance(insights, list) or not all(isinstance(insight, str) for insight in insights):
                raise ValueError("Insights Agent must return a list containing only strings.")
            if not insights:
                raise ValueError("Insights Agent returned an empty list.")
            
            # Return first 8 insights
            return insights[:8]
            
        except Exception as error:
            raise RuntimeError(f"Insight generation failed for question '{user_question}': {error}") from error
