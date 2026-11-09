
import pandas as pd
from pprint import pprint

from src.utils.llm_utils import (
    get_llm,
    invoke_llm,
    load_prompt,
    parse_structured_response
)


class VisualizationGenerator:

    # Configure the visualization planning model.
    def __init__(self, llm_model: str = "gemini-3.5-flash-lite", model_provider: str = "google_genai", temperature: float = 0.0):
        self.llm_model = llm_model
        self.model_provider = model_provider
        # self.temperature = temperature

    # Validate and construct one visualization from actual dataset values.
    def _build_visualization(self, specification: dict, query_result: pd.DataFrame) -> dict:
        try:
            chart_type = specification.get("chart_type")
            supported_types = {"bar", "line", "pie", "scatter"}

            if chart_type not in supported_types:
                raise ValueError(f"Unsupported chart type: {chart_type}.")

            x_column = specification.get("x_column")
            y_column = specification.get("y_column")

            if x_column not in query_result.columns or y_column not in query_result.columns:
                raise ValueError("Visualization references unavailable columns.")

            chart_data = query_result[[x_column, y_column]].copy().dropna().head(100)
            chart_data[y_column] = pd.to_numeric(chart_data[y_column], errors="coerce")
            chart_data = chart_data.dropna(subset=[y_column])

            if chart_type == "scatter":
                chart_data[x_column] = pd.to_numeric(chart_data[x_column], errors="coerce")
                chart_data = chart_data.dropna(subset=[x_column])

            if chart_data.empty:
                raise ValueError("Selected columns do not contain usable values.")

            if chart_type == "pie" and (chart_data[y_column] < 0).any():
                raise ValueError("Pie charts cannot contain negative values.")

            return {
                "create_visualization": True,
                "chart_type": chart_type,
                "title": specification.get("title", "IPL Analysis"),
                "description": specification.get("description", ""),
                "x_column": x_column,
                "y_column": y_column,
                "x_labels": chart_data[x_column].astype(str).tolist(),
                "x_values": (
                    chart_data[x_column].astype(float).tolist()
                    if chart_type == "scatter"
                    else chart_data[x_column].astype(str).tolist()
                ),
                "y_values": chart_data[y_column].astype(float).tolist()
            }

        except Exception as error:
            raise RuntimeError(f"Unable to build visualization: {error}") from error

    # Generate up to three visualizations for an analytical dataset.
    def run(self, user_question: str, query_result: pd.DataFrame) -> list[dict]:
        try:
            print("[VISUALIZATION AGENT] Planning visualizations.")

            if query_result.empty:
                return []

            llm = get_llm(self.llm_model, self.model_provider)
            system_prompt = load_prompt("./src/prompts/sql_visualization_system_prompt.txt")
            user_prompt = load_prompt("./src/prompts/sql_visualization_user_prompt.txt").format(
                user_question=user_question,
                query_result=query_result.head(100).to_string(index=False),
                result_columns=list(query_result.columns)
            )

            response = invoke_llm(
                llm,
                system_prompt,
                user_prompt,
                "visualization_planning"
            )

            specifications = parse_structured_response(response, "Visualization Agent")

            if isinstance(specifications, dict):
                if not specifications.get("create_visualization", False):
                    return []
                specifications = [specifications]

            if not isinstance(specifications, list):
                raise ValueError("Visualization Agent must return a list or dictionary.")

            visualizations = []

            for specification in specifications[:3]:
                if not isinstance(specification, dict):
                    continue
                if not specification.get("create_visualization", False):
                    continue

                try:
                    visualizations.append(
                        self._build_visualization(specification, query_result)
                    )
                except Exception as error:
                    print(f"[VISUALIZATION AGENT] Skipping invalid chart: {error}")

            for llist in visualizations:
                pprint(llist)
            return visualizations

        except Exception as error:
            raise RuntimeError(
                f"Visualization planning failed for '{user_question}': {error}"
            ) from error
