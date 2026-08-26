import json
import pandas as pd

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()


class MasterDecisionAgent:

    def __init__(
        self,
        llm_model: str = "openai/gpt-oss-120b",
        model_provider: str = "groq",
        temperature: float = 0
    ):
        self.llm_model = llm_model
        self.model_provider = model_provider
        self.temperature = temperature

        self.system_prompt_path = (
            "prompts/sql_master_decision_system_prompt.txt"
        )

    def run(self, state) -> dict:

        llm = init_chat_model(
            model=self.llm_model,
            model_provider=self.model_provider,
            temperature=self.temperature
        )

        # Load system prompt
        with open(self.system_prompt_path, "r") as file:
            system_prompt = file.read()

        # Convert query result into a readable representation
        if isinstance(state.query_result, pd.DataFrame):
            query_result = state.query_result.to_string(index=False)
        else:
            query_result = str(state.query_result)

        # Prepare current state for the Master Agent
        state_summary = {
            "user_question": state.user_question,
            "selected_tables": state.selected_tables,
            "generated_sql": state.generated_sql,
            "validation_errors": state.validation_errors,
            "query_result": query_result,

            "requires_deeper_analysis": (
                state.requires_deeper_analysis
            ),

            "required_grain": state.required_grain,
            "required_metrics": state.required_metrics,
            "identified_entities": state.identified_entities,

            "kpis": state.kpis,
            "insights": state.insights,
            "visualizations": state.visualizations,

            "completed_agents": state.completed_agents,
            "iteration": state.iteration
        }

        user_prompt = f"""
Here is the current state of the IPL analysis system:

{json.dumps(state_summary, indent=2, default=str)}

Based on the current state, decide which ONE agent should execute next.

Return ONLY valid JSON using exactly this structure:

{{
    "next_agent": "agent_name",
    "reason": "short explanation"
}}
"""

        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])

        response_text = str(response.content).strip()

        # Handle accidental markdown code fences
        if response_text.startswith("```"):
            response_text = (
                response_text
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )

        try:
            decision = json.loads(response_text)

        except json.JSONDecodeError:
            raise ValueError(
                "Master Decision Agent returned invalid JSON:\n"
                f"{response_text}"
            )

        # Validate response structure
        if "next_agent" not in decision:
            raise ValueError(
                "Master Decision Agent response does not contain "
                "'next_agent'."
            )

        if "reason" not in decision:
            raise ValueError(
                "Master Decision Agent response does not contain "
                "'reason'."
            )

        return decision