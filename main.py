from utils.sql_context_dataclass import SQLAgentContext
from agents.sql_agent import SQLAgent
from agents.table_selector_agent import TableSelectorAgent
from agents.master_agent import MasterAgent
from agents.sql_executor import SQLExecutor
from agents.insights_agent import InsightGenerator
from agents.kpi_agent import KPIGenerator
from agents.visualization_agent import VisualizationGenerator
from agents.master_decision_agent import MasterDecisionAgent
from pprint import pprint

# import requests
# import os

# api_key = os.environ.get("GROQ_API_KEY")
# url = "https://api.groq.com/openai/v1/models"

# headers = {
#     "Authorization": f"Bearer {api_key}",
#     "Content-Type": "application/json"
# }

# response = requests.get(url, headers=headers)
# models = [i['name'] for i in response.json()['data']]
# print(models)

question = "How has kohli's batting improved over the years?"


sql_context = SQLAgentContext(user_question=question)
master_agent = MasterAgent(
    table_selector=TableSelectorAgent(),
    sql_generator=SQLAgent(),
    sql_executor=SQLExecutor(),
    insights_generator=InsightGenerator(),
    kpi_generator=KPIGenerator(),
    visualization_generator=VisualizationGenerator(),
    master_decision_taker=MasterDecisionAgent()
)


sql_context = master_agent.run(question)