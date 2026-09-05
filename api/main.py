import json
from queue import Queue
from threading import Thread
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agents.insights_agent import InsightGenerator
from agents.kpi_agent import KPIGenerator
from agents.master_agent import MasterAgent
from agents.master_decision_agent import MasterDecisionAgent
from agents.sql_agent import SQLAgent
from agents.sql_executor import SQLExecutor
from agents.table_selector_agent import TableSelectorAgent
from agents.visualization_agent import VisualizationGenerator


app = FastAPI(title="IPL Analytics Chat API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    conversation_id: str | None = None


def create_master_agent() -> MasterAgent:
    return MasterAgent(
        table_selector=TableSelectorAgent(),
        sql_generator=SQLAgent(),
        sql_executor=SQLExecutor(),
        insights_generator=InsightGenerator(),
        kpi_generator=KPIGenerator(),
        visualization_generator=VisualizationGenerator(),
        master_decision_taker=MasterDecisionAgent(),
    )


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/chat/stream")
def stream_chat(request: ChatRequest):
    """Stream orchestration progress followed by a SQL-free final response."""
    conversation_id = request.conversation_id or str(uuid4())
    events: Queue[tuple[str, dict] | None] = Queue()

    def on_progress(stage: str, message: str) -> None:
        events.put(("progress", {"conversation_id": conversation_id, "stage": stage, "message": message}))

    def run_analysis() -> None:
        try:
            state = create_master_agent().run(request.message.strip(), on_progress=on_progress)
            if state.next_agent == "no_data":
                events.put(("complete", {
                    "conversation_id": conversation_id,
                    "status": "no_data",
                    "message": "No relevant data found.",
                    "kpis": None,
                    "insights": [],
                    "visualization": None,
                }))
            else:
                events.put(("complete", {
                    "conversation_id": conversation_id,
                    "status": "complete",
                    "kpis": state.kpis,
                    "insights": state.insights,
                    "visualization": state.visualizations,
                }))
        except Exception:
            events.put(("error", {
                "conversation_id": conversation_id,
                "message": "Unable to complete the IPL analysis. Please try again.",
            }))
        finally:
            events.put(None)

    Thread(target=run_analysis, daemon=True).start()

    def event_stream():
        while (item := events.get()) is not None:
            event, data = item
            yield sse(event, data)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
