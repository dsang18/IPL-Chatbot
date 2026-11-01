
from src.agents.insights_agent import InsightGenerator
from src.agents.kpi_agent import KPIGenerator
from src.agents.master_agent import MasterAgent
from src.agents.sql_agent import SQLAgent
from src.agents.sql_executor import SQLExecutor
from src.agents.table_selector_agent import TableSelectorAgent
from src.agents.visualization_agent import VisualizationGenerator


# Create the agents required for IPL analysis.
def create_master_agent() -> MasterAgent:
    try:
        return MasterAgent(
            table_selector=TableSelectorAgent(), 
            sql_generator=SQLAgent(), 
            sql_executor=SQLExecutor(), 
            insights_generator=InsightGenerator(), 
            kpi_generator=KPIGenerator(), 
            visualization_generator=VisualizationGenerator()
        )
    except Exception as error:
        raise RuntimeError(f"Unable to initialise the IPL analysis workflow: {error}") from error


# Run the IPL analysis workflow using an interactive question.
def main() -> None:
    try:
        question = input("Enter your IPL question: ").strip()
        if not question:
            raise ValueError("The question cannot be empty.")
        print("[MAIN] Starting IPL analysis.")
        result = create_master_agent().run(question)
        print("\nKPIs:")
        print(result.kpis)
        print("\nInsights:")
        print(result.insights)
        print("\nVisualization:")
        print(result.visualizations)
    except Exception as error:
        print(f"[MAIN] IPL analysis failed: {error}")


if __name__ == "__main__":
    main()
