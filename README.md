# 🏏 IPL Chatbot

**An AI-powered conversational analytics assistant for IPL cricket data.**

IPL Insights allows users to explore IPL statistics using natural-language questions. It translates questions into SQL queries, retrieves insights from a DuckDB database, and presents analytical results through tables, KPIs and visualizations.

## ✨ Key Features

- **Natural Language to SQL:** Convert cricket-related questions into executable DuckDB queries.
- **Multi-Agent Architecture:** Specialized agents handle query planning, SQL generation, execution, insights and visualization.
- **Conversational Memory:** Retain conversation history and context across follow-up questions.
- **Context-Aware Understanding:** Interpret follow-up questions using previous analytical results.
- **Intelligent Clarification:** Identify ambiguous questions and request additional information.
- **Multi-Step Reasoning:** Break complex analytical questions into dependent steps and synthesize their results.
- **Automated Insights & KPIs:** Generate meaningful statistical observations and performance indicators.
- **Interactive Visualizations:** Present analytical findings through charts and data tables.

## 🏗️ Architecture

The application uses a multi-agent workflow coordinated by a Master Agent.

| Agent / Component | Responsibility |
|---|---|
| Master Agent | Orchestrates the analytical workflow |
| Query Planner | Understands questions and creates analytical plans |
| SQL Generator | Generates and validates SQL queries |
| SQL Executor | Executes queries against DuckDB |
| KPI Generator | Generates relevant performance indicators |
| Insights Generator | Extracts meaningful analytical observations |
| Visualization Generator | Creates suitable visualizations |
| Conversation Context Agent | Resolves follow-ups and handles clarification |
| Result Synthesizer | Combines results from multi-step analysis |

**Workflow:** User Question → Query Planning → SQL Generation → SQL Execution → KPI & Insights Generation → Visualization → Final Response.

Complex questions can follow a multi-step execution path with intermediate-result sharing and final synthesis.

## 🛠️ Technology Stack

- **Language:** Python
- **Backend:** FastAPI
- **Frontend:** HTML, CSS, JavaScript
- **Database:** DuckDB
- **Conversation Storage:** SQLite
- **AI Framework:** LangChain
- **LLM Provider:** Google Gemini

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Required LLM provider API credentials

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/dsang18/IPL-Chatbot.git
   cd IPL-Chatbot
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Configure the required API credentials and environment variables.

5. Start the application:

   ```bash
   python -m uvicorn src.api.main:app --reload
   ```

6. Open the application at:

   `http://127.0.0.1:8000`

## 💡 Example Questions

- Who scored the most runs in IPL history?
- Which are the best-performing bowlers at Wankhede?
- Compare a team's performance across two IPL seasons.
- How has Virat Kohli's batting performance evolved over the years?
- Which players have performed best in death overs?

## 🎯 Project Objective

IPL Insights is a personal portfolio project demonstrating the practical application of **Agentic AI, Natural Language to SQL, multi-step analytical reasoning, conversational AI and data analytics engineering**.