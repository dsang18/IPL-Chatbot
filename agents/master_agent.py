from utils.sql_context_dataclass import SQLAgentContext
from utils.schema_loader import load_database_schema,load_custom_database_schema, get_database_schema_metadata

class MasterAgent:

    def __init__(self,table_selector,sql_generator,sql_validator,sql_executor, deeper_analysis_checker,insights_generator,kpi_generator,visualization_generator, master_decision_taker):
        self.table_selector = table_selector
        self.sql_generator = sql_generator
        self.sql_validator = sql_validator
        self.sql_executor = sql_executor
        self.deeper_analysis_checker = deeper_analysis_checker
        self.insights_generator = insights_generator
        self.kpi_generator = kpi_generator
        self.visualization_generator = visualization_generator
        self.master_decision_agent = master_decision_taker

    def run(self, user_question: str):
        state = SQLAgentContext(user_question=user_question)
        schema = load_database_schema(state.database_schema_path)
        while state.iteration < state.max_iterations:
            state.iteration += 1
            decision = self.master_decision_agent.run(state)
            state.next_agent = decision["next_agent"]
            print(f"Master Agent -> {state.next_agent}")
            print(f"Reason -> {decision['reason']}")
            if state.next_agent=="complete":
                break
            self.execute_agent(state.next_agent, state, schema)
            state.completed_agents.append(state.next_agent)
            state.validation_errors = []
        return state


    def execute_agent(self, agent_name: str, state: SQLAgentContext, schema={}):

        if agent_name == "table_selector":
            metadata_schema = get_database_schema_metadata(schema)

            state.selected_tables = self.table_selector.run(state.user_question,metadata_schema)

            print(f"\nTables selected:\n{state.selected_tables}")


        elif agent_name == "sql_generator":

            custom_schema = load_custom_database_schema(database_schema=schema,tables=state.selected_tables)
            state.generated_sql = self.sql_generator.run(
                user_question=state.user_question,
                database_schema=custom_schema,
                previous_result=state.query_result,
                required_grain=state.required_grain,
                required_metrics=state.required_metrics,
                identified_entities=state.identified_entities,
                validation_errors=state.validation_errors,
                generated_sql=state.generated_sql
            )
            print(f"\nGenerated SQL:\n{state.generated_sql}")


        elif agent_name == "sql_validator":
            validation_result = self.sql_validator.validate(state.generated_sql,schema)
            state.validation_errors = validation_result["errors"]
            print(f"\nSQL Valid: {validation_result['valid']}")
            print(f"Validation Errors: {state.validation_errors}")


        elif agent_name == "sql_executor":

            state.query_result = self.sql_executor.run(
                state.generated_sql
            )

            print(
                f"\nQuery Result:\n{state.query_result}"
            )


        elif agent_name == "deeper_analysis_checker":

            decision = self.deeper_analysis_checker.run(
                user_question=state.user_question,
                query_result=state.query_result
            )

            state.requires_deeper_analysis = (
                decision["requires_deeper_analysis"]
            )

            state.required_grain = str(
                decision.get("required_grain", "")
            )

            state.required_metrics = decision.get(
                "required_metrics",
                []
            )

            state.identified_entities = decision.get(
                "identified_entities",
                []
            )

            print(
                f"\nDeeper Analysis Decision:\n{decision}"
            )


        elif agent_name == "insights_generator":

            state.insights = self.insights_generator.run(
                user_question=state.user_question,
                query_result=state.query_result
            )

            print(
                f"\nInsights:\n{state.insights}"
            )


        elif agent_name == "kpi_generator":

            state.kpis = self.kpi_generator.run(
                user_question=state.user_question,
                query_result=state.query_result
            )

            print(
                f"\nKPIs:\n{state.kpis}"
            )


        elif agent_name == "visualization_generator":

            state.visualizations = (
                self.visualization_generator.run(
                    user_question=state.user_question,
                    query_result=state.query_result
                )
            )

            print(
                f"\nVisualization:\n{state.visualizations}"
            )


        else:

            raise ValueError(
                f"Unknown agent: {agent_name}"
            )
    # def run(self, user_question: str):

    #     state = SQLAgentContext(user_question=user_question)

    #     state.iteration += 1
    #     # Load the database schema from a YAML file
    #     schema = load_database_schema(state.database_schema_path)

    #     metadata_schema = get_database_schema_metadata(schema)
    #     state.selected_tables = self.table_selector.run(user_question, metadata_schema)

    #     print(f"\nTables selected for the user's question: {state.selected_tables}")

    #     # Load the custom database schema based on the decided tables
    #     custom_schema = load_custom_database_schema(database_schema=schema, tables=state.selected_tables)

    #     state.generated_sql = self.sql_generator.run(user_question,custom_schema)
    #     print(f"\nGenerated SQL query: {state.generated_sql}")

    #     validation_result = self.sql_validator.validate(state.generated_sql, schema)
    #     print(f"\nValidation result: {validation_result['valid']}\nErrors: {validation_result['errors']}")
    #     state.validation_errors = validation_result['errors']
    
    #     while validation_result['valid'] == False and state.iteration < state.max_iterations:
    #         state.validation_errors = validation_result['errors']
    #         state.generated_sql = self.sql_generator.run(user_question,custom_schema,validation_errors=state.validation_errors,generated_sql=state.generated_sql)
    #         validation_result = self.sql_validator.validate(state.generated_sql, schema)
    #         print(f"\nGenerated SQL query after validation: {state.generated_sql}")
        
    #     state.query_result = self.sql_executor.run(state.generated_sql)
    #     print(f"\nQuery result:\n{state.query_result}")

    #     while state.query_result.shape[0] == 0 and state.iteration < state.max_iterations:
    #         state.validation_errors = ["Empty result set returned from the query execution. Please generate a corrected SQL query."]
    #         state.generated_sql = self.sql_generator.run(user_question,custom_schema,validation_errors=state.validation_errors,generated_sql=state.generated_sql)
    #         validation_result = self.sql_validator.validate(state.generated_sql, schema)
    #         print(f"\nGenerated SQL query after validation: {state.generated_sql}")
    #         state.query_result = self.sql_executor.run(state.generated_sql)
    #         print(f"\nQuery result:\n{state.query_result}")
            

    #     # -----------------------------------------
    #     # Master Agent decision
    #     # -----------------------------------------

    #     decision = self.deeper_analysis_checker.run(user_question=user_question, query_result=state.query_result)

    #     state.requires_deeper_analysis = decision["requires_deeper_analysis"]

    #     print(f"\nDeeper analysis is required for the user's question:\n{decision}")

    #     if not state.requires_deeper_analysis:
    #         return state


    #     # -----------------------------------------
    #     # Iteration 2: Generate detailed query
    #     # -----------------------------------------

    #     state.required_grain = str(decision["required_grain"])
    #     # state.required_metrics = decision.get("required_metrics", [])
    #     state.identified_entities = decision.get("identified_entities", [])

        
    #     state.generated_sql = self.sql_generator.run(
    #         user_question=user_question,
    #         database_schema=custom_schema,
    #         previous_result=state.query_result,
    #         required_grain=state.required_grain,
    #         # required_metrics=state.required_metrics,
    #         identified_entities=state.identified_entities,
    #     )
    #     print(f"\nGenerated SQL query for deeper analysis: {state.generated_sql}")

    #     validation_result = self.sql_validator.validate(state.generated_sql, schema)
    #     print(f"\nValidation result: {validation_result['valid']}\nErrors: {validation_result['errors']}")
    #     state.validation_errors = validation_result['errors']
    
    #     while validation_result['valid'] == False and state.iteration < state.max_iterations:
    #         state.validation_errors = validation_result['errors']
    #         state.generated_sql = self.sql_generator.run(user_question,custom_schema,validation_errors=state.validation_errors,generated_sql=state.generated_sql)
    #         validation_result = self.sql_validator.validate(state.generated_sql, schema)
    #         print(f"\nGenerated SQL query after validation: {state.generated_sql}")
        
    #     state.query_result = self.sql_executor.run(state.generated_sql)
    #     print(f"\nQuery result:\n{state.query_result}")

    #     while state.query_result.shape[0] == 0 and state.iteration < state.max_iterations:
    #         state.validation_errors = ["Empty result set returned from the query execution. Please generate a corrected SQL query."]
    #         state.generated_sql = self.sql_generator.run(user_question,custom_schema,validation_errors=state.validation_errors,generated_sql=state.generated_sql)
    #         validation_result = self.sql_validator.validate(state.generated_sql, schema)
    #         print(f"\nGenerated SQL query after validation: {state.generated_sql}")
    #         state.query_result = self.sql_executor.run(state.generated_sql)
    #         print(f"\nQuery result:\n{state.query_result}")


    #     insights_generator = self.insights_generator
    #     state.insights = insights_generator.run(user_question=user_question, query_result=state.query_result)

    #     print(f"\nInsights generated for the user's question:\n{state.insights}")

    #     kpi_generator = self.kpi_generator
    #     state.kpis = kpi_generator.run(user_question=user_question, query_result=state.query_result)
    #     print(f"\nKPIs generated for the user's question:\n{state.kpis}")

    #     visualization_generator = self.visualization_generator
    #     state.visualizations = visualization_generator.run(user_question=user_question, query_result=state.query_result)
    #     print(f"\nVisualizations generated for the user's question:\n{state.visualizations}")

    #     return state




