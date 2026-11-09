
import pandas as pd

from src.utils.llm_utils import get_llm, invoke_llm, load_prompt, parse_structured_response


class VisualizationGenerator:

    # Configure the visualization planning model.
    def __init__(self, llm_model: str = "gemini-3.5-flash-lite", model_provider: str = "google_genai", temperature: float = 0.0):
        self.llm_model = llm_model
        self.model_provider = model_provider
        self.temperature = temperature

    # Generate a visualization specification using actual query-result values.
    def run(self, user_question: str, query_result: pd.DataFrame) -> dict:
        try:
            print("[VISUALIZATION AGENT] Planning visualization.")

            # Check if the SQL query result is empty
            if query_result.empty:
                return {"create_visualization": False, "reason": "The analytical dataset is empty."}
            
            # Initialize the LLM variables
            llm = get_llm(self.llm_model, self.model_provider, self.temperature)
            system_prompt = load_prompt("./src/prompts/sql_visualization_system_prompt.txt")
            user_prompt = load_prompt("./src/prompts/sql_visualization_user_prompt.txt").format(
                user_question=user_question, 
                query_result=query_result.head(100).to_string(index=False), 
                result_columns=list(query_result.columns)
            )

            # Invoke LLM to generate raw data for a chart
            response = invoke_llm(llm, system_prompt, user_prompt, "visualization_planning")
            visualization = parse_structured_response(response, "Visualization Agent")

            # Check if the response is a dictionary
            if not isinstance(visualization, dict):
                raise ValueError("Visualization Agent must return a JSON dictionary.")
            if not visualization.get("create_visualization", False):
                return {"create_visualization": False, "reason": visualization.get("reason", "Visualization is not required.")}

            # Check if the chart type is within options
            chart_type = visualization.get("chart_type")
            if chart_type not in {"bar", "line", "pie", "scatter"}:
                raise ValueError(f"Unsupported chart type: {chart_type}.")
            
            # Check if the columns used are in the response
            x_column = visualization.get("x_column")
            y_column = visualization.get("y_column")
            if x_column not in query_result.columns or y_column not in query_result.columns:
                raise ValueError(f"Invalid visualization columns. Available columns: {list(query_result.columns)}.")
            
            # Initalize Chart data
            chart_data = query_result[[x_column, y_column]].copy().dropna().head(100)
            chart_data[y_column] = pd.to_numeric(chart_data[y_column], errors="coerce")
            chart_data = chart_data.dropna(subset=[y_column])
            if chart_type == "scatter":
                chart_data[x_column] = pd.to_numeric(chart_data[x_column], errors="coerce")
                chart_data = chart_data.dropna(subset=[x_column])
            if chart_data.empty:
                raise ValueError("The selected visualization columns do not contain usable values.")
            if chart_type == "pie" and (chart_data[y_column] < 0).any():
                raise ValueError("Pie charts cannot represent negative values.")
            
            return {
                "create_visualization": True,
                "chart_type": chart_type,
                "title": visualization.get("title", "IPL Analysis"),
                "description": visualization.get("description", ""),
                "x_column": x_column,
                "y_column": y_column,
                "x_labels": chart_data[x_column].astype(str).tolist(),
                "x_values": chart_data[x_column].astype(float).tolist() if chart_type == "scatter" else chart_data[x_column].astype(str).tolist(),
                "y_values": chart_data[y_column].astype(float).tolist(),
            }

            
        except Exception as error:
            raise RuntimeError(f"Visualization planning failed for question '{user_question}': {error}") from error
