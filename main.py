from utils.sql_context_dataclass import SQLAgentContext
from agents.sql_agent import generate_sql
from utils.database import execute_query
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

question = "Who has taken most wickets against chennai in IPL?"


sql_context = SQLAgentContext(user_question=question)
sql_context = generate_sql(sql_context)
print(sql_context.generated_sql)

if (sql_context.is_valid):
    sql_query_result = execute_query(sql_context.generated_sql)
else:
    sql_query_result = {"error": "SQL query is not valid. Please check the validation errors."}


print("\n\n"+f"="*100)
print(f"SQL Query Context")
print(f"="*100)
pprint(sql_context)
print(f"="*100)

print("\n\n"+f"="*100)
print(f"SQL Query Result")
print(f"="*100)
pprint(sql_query_result)
print(f"="*100)