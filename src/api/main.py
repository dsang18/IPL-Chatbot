
import json
import logging
from queue import Queue
from threading import BoundedSemaphore, Thread
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from src.agents.insights_agent import InsightGenerator
from src.agents.kpi_agent import KPIGenerator
from src.agents.master_agent import MasterAgent
from src.agents.sql_agent import SQLAgent
from src.agents.sql_executor import SQLExecutor
from src.agents.table_selector_agent import TableSelectorAgent
from src.agents.visualization_agent import VisualizationGenerator


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="IPL Analytics Chat API", version="0.2.0")
ANALYSIS_SEMAPHORE = BoundedSemaphore(4)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    conversation_id: str | None = None

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("The question cannot contain only whitespace.")
        return value.strip()


# Create the agents required for one analysis request.
def create_master_agent() -> MasterAgent:
    try:
        print("[API] Initialising analysis agents.")
        return MasterAgent(
            table_selector=TableSelectorAgent(), 
            sql_generator=SQLAgent(), 
            sql_executor=SQLExecutor(), 
            insights_generator=InsightGenerator(), 
            kpi_generator=KPIGenerator(), 
            visualization_generator=VisualizationGenerator()
        )
    except Exception as error:
        raise RuntimeError(f"Unable to initialise the IPL analysis agents: {error}") from error


# Format an event as a Server-Sent Event message.
def sse(event: str, data: dict) -> str:
    try:
        return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"
    except Exception as error:
        raise RuntimeError(f"Unable to serialise SSE event '{event}': {error}") from error


# Return the API health status.
@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "service": "ipl-analytics-api"}


# Stream analysis progress and the final SQL-free result.
@app.post("/api/chat/stream")
def stream_chat(request: ChatRequest):
    if not ANALYSIS_SEMAPHORE.acquire(blocking=False):
        raise HTTPException(status_code=503, detail="The analytics service is busy. Please try again shortly.")

    conversation_id = request.conversation_id or str(uuid4())
    events: Queue[tuple[str, dict] | None] = Queue()

    # Add an orchestration progress event to the stream.
    def on_progress(stage: str, message: str) -> None:
        events.put(("progress", {"conversation_id": conversation_id, "stage": stage, "message": message}))

    # Run the analysis in a background thread and publish its final result.
    def run_analysis() -> None:
        try:
            logger.info("Analysis started. Conversation ID: %s", conversation_id)
            state = create_master_agent().run(request.message, on_progress=on_progress)
            if state.next_agent == "no_data":
                result = {"conversation_id": conversation_id, "status": "no_data", "message": "No relevant data found.", "kpis": {}, "insights": [], "visualization": None}
            else:
                result = {"conversation_id": conversation_id, "status": "complete", "kpis": state.kpis, "insights": state.insights, "visualization": state.visualizations}
            events.put(("complete", result))
            logger.info("Analysis completed. Conversation ID: %s", conversation_id)
        except Exception as error:
            logger.exception("Analysis failed. Conversation ID: %s. Error: %s", conversation_id, error)
            events.put(("error", {"conversation_id": conversation_id, "message": "Unable to complete the IPL analysis. Please try again."}))
        finally:
            ANALYSIS_SEMAPHORE.release()
            events.put(None)

    # Stream queued progress and result events to the client.
    def event_stream():
        try:
            while True:
                item = events.get()
                if item is None:
                    break
                event, data = item
                yield sse(event, data)
        except Exception as error:
            logger.exception("SSE streaming failed. Conversation ID: %s. Error: %s", conversation_id, error)

    try:
        Thread(target=run_analysis, daemon=True).start()
        return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
    except Exception as error:
        ANALYSIS_SEMAPHORE.release()
        raise RuntimeError(f"Unable to start the analysis stream: {error}") from error
