
import json

from src.utils.llm_utils import get_llm, invoke_llm, load_prompt, parse_structured_response


class ResultSynthesizer:

    # Configure the result synthesis model.
    def __init__(self, llm_model: str = "gemini-3.5-flash-lite", model_provider: str = "google_genai", temperature: float = 0.0):
        self.llm_model = llm_model
        self.model_provider = model_provider
        self.temperature = temperature

    # Combine the results of completed analytical steps into a grounded explanation.
    def run(self, user_question: str, analytical_plan: dict, execution_trace: list[dict]) -> dict:
        try:
            print("[RESULT SYNTHESIZER] Preparing multi-step findings.")
            completed_steps = [step for step in execution_trace if step.get("status") == "completed"]
            if not completed_steps:
                raise ValueError("No completed analytical steps are available for synthesis.")

            llm = get_llm(self.llm_model, self.model_provider, self.temperature)
            system_prompt = load_prompt("./src/prompts/result_synthesizer_system_prompt.txt")
            synthesis_input = {"question": user_question, "plan": analytical_plan.get("steps", []), "results": [{"step_id": step["step_id"], "objective": step["objective"], "row_count": step["row_count"], "columns": step["columns"], "result_preview": step["result_preview"]} for step in completed_steps]}
            user_prompt = load_prompt("./src/prompts/result_synthesizer_user_prompt.txt").format(analysis_data=json.dumps(synthesis_input, separators=(",", ":"), default=str))
            response = invoke_llm(llm, system_prompt, user_prompt, "result_synthesis")
            synthesis = parse_structured_response(response, "Result Synthesizer")

            if not isinstance(synthesis, dict) or not isinstance(synthesis.get("summary"), str) or not synthesis["summary"].strip():
                raise ValueError("Result synthesis must contain a non-empty summary.")
            if not isinstance(synthesis.get("insights"), list) or not all(isinstance(item, str) for item in synthesis["insights"]):
                raise ValueError("Result synthesis insights must be a list of strings.")

            synthesis["insights"] = synthesis["insights"][:8]
            print(f"[RESULT SYNTHESIZER] Synthesis completed using {len(completed_steps)} steps.")
            return synthesis
        except Exception as error:
            raise RuntimeError(f"Result synthesis failed for '{user_question}': {error}") from error
