
import pandas as pd

from src.utils.llm_utils import get_llm, invoke_llm, load_prompt, parse_structured_response


class KPIGenerator:

    # Configure the KPI generation model.
    def __init__(self, llm_model: str = "gemini-3.5-flash-lite", model_provider: str = "google_genai", temperature: float = 0.0):
        self.llm_model = llm_model
        self.model_provider = model_provider
        self.temperature = temperature

    # Generate four to six relevant KPIs from the analytical dataset.
    def run(self, user_question: str, query_result: pd.DataFrame) -> dict:
        try:
            print("[KPI AGENT] Generating KPIs.")

            # Check if the result of the sql query is empty
            if query_result.empty:
                raise ValueError("Cannot generate KPIs from an empty dataset.")
            
            # Initialize the LLM variables
            llm = get_llm(self.llm_model, self.model_provider, self.temperature)
            system_prompt = load_prompt("./src/prompts/sql_kpi_system_prompt.txt")
            user_prompt = load_prompt("./src/prompts/sql_kpi_user_prompt.txt").format(
                user_question=user_question, 
                query_result=query_result.head(200).to_string(index=False)
            )

            # Invoke LLM to generate KPIs
            response = invoke_llm(llm, system_prompt, user_prompt, "kpi_generation")
            kpis = parse_structured_response(response, "KPI Agent")

            # Check if there are 4 to 6 KPIs generated
            if not isinstance(kpis, dict) or not 1 <= len(kpis) <= 6:
                raise ValueError(f"KPI Agent must return 4 to 6 KPIs. Received: {len(kpis) if isinstance(kpis, dict) else type(kpis).__name__}.")

            for key, value in kpis.items():
                print(f"• {key} ➜ {value}")
            return kpis
        
        except Exception as error:
            raise RuntimeError(f"KPI generation failed for question '{user_question}': {error}") from error
