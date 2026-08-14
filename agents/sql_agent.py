import os
from pathlib import Path
from utils.sql_context_dataclass import SQLAgentContext
from langchain.chat_models import init_chat_model
import ast
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage

from utils.schema_loader import load_database_schema,get_database_schema_metadata, load_custom_database_schema
from utils.database import validate_query

load_dotenv()

os.environ["GROQ_API_KEY"] = str(os.getenv("GROQ_API_KEY"))


def generate_sql(sql_context: SQLAgentContext) -> SQLAgentContext:
    """
    Generate SQL query based on the user's question.

    Args:
        user_question (str): The user's question for which to generate an SQL query.

    Returns:
        str: The generated SQL query.
    """


    # Initalize the LLM with llama model
    llm = init_chat_model(
        model="openai/gpt-oss-120b",
        model_provider="groq",
        temperature=1
    )

    user_question = sql_context.user_question
    SCHEMA_PATH = sql_context.database_schema_path
    SYSTEM_PROMPT_PATH = sql_context.prompt_paths["sql_query_system_prompt"]
    USER_PROMPT_PATH = sql_context.prompt_paths["sql_query_user_prompt"]

    # Load the database schema from a YAML file
    schema = load_database_schema(SCHEMA_PATH)
    sql_context = decide_tables(sql_context)

    print(f"Tables decided for the user's question: {sql_context.selected_tables}")

    # Load the custom database schema based on the decided tables
    custom_schema = load_custom_database_schema(database_schema=schema, tables=sql_context.selected_tables)

    print(f"Database schema loaded from {SCHEMA_PATH}.")

    with open(SYSTEM_PROMPT_PATH, 'r') as file:
            prompt_template = file.read()

    system_prompt = prompt_template.format()

    # Load the prompt template from a text file
    with open(USER_PROMPT_PATH, 'r') as file:
        prompt_template = file.read()

    # print(f"Prompt template loaded from {PROMPT_PATH}.")

    # Format the prompt with the user's question and the database schema
    prompt = prompt_template.format(user_question=user_question, database_schema=custom_schema)
    print(f"Prompt generated for the user's question: {user_question}")

    # Generate SQL using Ollama's API
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=prompt)
    ])
    
    sql_query = str(response.content).strip()

    print(f"Validating the generated SQL query against the database schema...")
    validation_results = validate_query(query=sql_query, schema_file_path=SCHEMA_PATH)

    if not validation_results["valid"]:
        for i in range(3):  # Retry up to 3 times
            print(f"Attempt {i+1}: The generated SQL query is not valid. Validation errors: {validation_results.get('errors', [])}\n")
            new_prompt_template = f"""
            {prompt}
            The generated SQL query is not valid. Please provide a corrected SQL query that adheres to the database schema and addresses the user's question.

            SQL Query: {sql_query}
            Validation Errors: {validation_results.get("errors", [])}

            """
            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=new_prompt_template)
            ])
            sql_query = str(response.content).strip()
            validation_results = validate_query(query=sql_query, schema_file_path=SCHEMA_PATH)
            if validation_results["valid"]:
                break        

    sql_context.generated_sql = str(response.content).strip()    
    sql_context.is_valid = validation_results["valid"]
    sql_context.validation_errors = validation_results.get("errors", [])

    return sql_context


def decide_tables(sql_context: SQLAgentContext) -> SQLAgentContext:
    """
    Decide which tables to use based on the database schema.

    Returns:
        list: A list of table names to be used in SQL generation.
    """

    # Initalize the LLM with llama model
    llm = init_chat_model(
        model="openai/gpt-oss-120b",
        model_provider="groq",
        temperature=0.2
    )

    user_question = sql_context.user_question
    SCHEMA_PATH = sql_context.database_schema_path
    SQL_SCHEMA_PROMPT_PATH = sql_context.prompt_paths["sql_tables_user_prompt"]
    
    # Load the database schema from a YAML file
    schema = load_database_schema(SCHEMA_PATH)
    print(f"Database schema loaded from {SCHEMA_PATH}.")

    # Extract table names from the schema
    table_names = list(schema['tables'].keys())
    print(f"Tables available in the database schema: {table_names}")

    metadata_schema = get_database_schema_metadata(schema)

    with open(SQL_SCHEMA_PROMPT_PATH, 'r') as file:
        prompt_template = file.read()

    prompt = prompt_template.format(user_question=user_question, database_schema=metadata_schema)

    # print(f"Prompt for deciding tables: {prompt}")

    response = llm.invoke(
        input=[
            HumanMessage(content=prompt)
        ],
    )
    print(f"Response from LLM for deciding tables: {response.content}")
    sql_context.selected_tables = ast.literal_eval(str(response.content).strip())

    return sql_context


