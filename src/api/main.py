
import json
import logging
from queue import Queue
from threading import BoundedSemaphore, Thread
from uuid import uuid4
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from src.agents.conversation_context_agent import resolve_conversation_context
from src.agents.insights_agent import InsightGenerator
from src.agents.kpi_agent import KPIGenerator
from src.agents.master_agent import MasterAgent
from src.agents.query_planner_agent import QueryPlannerAgent
from src.agents.sql_agent import SQLAgent
from src.agents.sql_executor import SQLExecutor
from src.agents.visualization_agent import VisualizationGenerator
from src.agents.result_synthesizer_agent import ResultSynthesizer
from src.utils.conversation_store import create_conversation, get_conversation, initialize_conversation_store, save_message, update_conversation_context


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="IPL Analytics Chat API", version="0.3.0")
ANALYSIS_SEMAPHORE = BoundedSemaphore(4)
initialize_conversation_store()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    conversation_id: str | None = Field(default=None, max_length=64)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("The question cannot contain only whitespace.")
        return value.strip()


# Initialise all agents required for single-step and multi-step analysis.
def create_master_agent() -> MasterAgent:
    try:
        print("[API] Initialising analysis agents.")
        return MasterAgent(query_planner=QueryPlannerAgent(), sql_generator=SQLAgent(), sql_executor=SQLExecutor(), insights_generator=InsightGenerator(), kpi_generator=KPIGenerator(), visualization_generator=VisualizationGenerator(), result_synthesizer=ResultSynthesizer())
    except Exception as error:
        raise RuntimeError(f"Unable to initialise the IPL analysis agents: {error}") from error

# Format an event as a Server-Sent Event message.
def sse(event: str, data: dict[str, Any]) -> str:
    try:
        return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"
    except Exception as error:
        raise RuntimeError(f"Unable to serialise SSE event '{event}': {error}") from error


# Build a compact context summary from a completed analytical result.
def build_conversation_context(state: Any) -> dict[str, Any]:
    try:
        print("[API] Building compact analytical conversation context.")
        return {"last_question": state.user_question, "intent": state.query_plan.get("intent", ""), "entities": state.query_plan.get("entities", []), "metrics": state.query_plan.get("metrics", []), "filters": state.query_plan.get("filters", []), "group_by": state.query_plan.get("group_by", []), "execution_mode": state.query_plan.get("execution_mode", "single"), "analytical_steps": [{"step_id": step["step_id"], "objective": step["objective"]} for step in state.analytical_steps], "result_preview": state.query_result.head(5).to_dict(orient="records")}
    except Exception as error:
        raise RuntimeError(f"Unable to build analytical conversation context: {error}") from error
    

# Create a concise assistant message for conversation history.
def build_assistant_answer(state: Any) -> str:
    try:
        if state.insights:
            return " ".join(str(insight) for insight in state.insights[:3])
        if not state.query_result.empty:
            return f"Analysis completed successfully with {len(state.query_result)} result rows."
        return "The analysis completed, but no explanatory insights were generated."
    except Exception as error:
        raise RuntimeError(f"Unable to create the assistant response summary: {error}") from error


# Return the API health status.
@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "ipl-analytics-api"}


# Retrieve a conversation so the frontend can restore its chat history.
@app.get("/api/conversations/{conversation_id}")
def retrieve_conversation(conversation_id: str) -> dict[str, Any]:
    try:
        conversation = get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        return conversation
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Unable to retrieve conversation %s: %s", conversation_id, error)
        raise HTTPException(status_code=500, detail="Unable to retrieve conversation history.") from error


# Stream conversational analysis and the final SQL-free result.
@app.post("/api/chat/stream")
def stream_chat(request: ChatRequest) -> StreamingResponse:
    if not ANALYSIS_SEMAPHORE.acquire(blocking=False):
        raise HTTPException(status_code=503, detail="The analytics service is busy. Please try again shortly.")

    conversation_id = request.conversation_id or str(uuid4())
    events: Queue[tuple[str, dict[str, Any]] | None] = Queue()

    # Add an orchestration progress event to the stream.
    def on_progress(stage: str, message: str) -> None:
        events.put(("progress", {"conversation_id": conversation_id, "stage": stage, "message": message}))

    # Run context resolution and analytical processing in a background thread.
    def run_analysis() -> None:
        try:
            logger.info("Analysis started. Conversation ID: %s", conversation_id)
            conversation = get_conversation(conversation_id)
            if conversation is None:
                create_conversation(conversation_id)
                conversation = {"context": {}, "messages": []}

            save_message(conversation_id, "user", request.message)
            resolution = resolve_conversation_context(request.message, conversation["messages"], conversation["context"])

            if resolution["needs_clarification"]:
                clarification = resolution["clarification_question"]
                save_message(conversation_id, "assistant", clarification)
                events.put(("complete", {"conversation_id": conversation_id, "status": "clarification", "message": clarification}))
                logger.info("Clarification requested. Conversation ID: %s", conversation_id)
                return

            standalone_question = resolution["standalone_question"]
            events.put(("progress", {"conversation_id": conversation_id, "stage": "context_resolution", "message": "Understanding your question and conversation context."}))
            state = create_master_agent().run(standalone_question, on_progress=on_progress, conversation_context=conversation["context"])

            if state.next_agent == "no_data":
                answer = state.query_plan.get("reason") or "I couldn't find relevant IPL data to answer that question."
                result = {"conversation_id": conversation_id, "status": "no_data", "message": answer, "kpis": {}, "insights": [], "visualizations": [], "table": {"columns": [], "rows": []}, "domain_analytics": {}}
            else:
                answer = build_assistant_answer(state)
                result = {"conversation_id": conversation_id, "status": "complete", "answer": answer, "kpis": state.kpis, "insights": state.insights, "visualizations": state.visualizations, "table": {"columns": state.query_result.columns.tolist(), "rows": state.query_result.head(100).to_dict(orient="records")}, "domain_analytics": state.domain_analytics}

            save_message(conversation_id, "assistant", answer)
            if result["status"] == "complete":
                update_conversation_context(conversation_id, build_conversation_context(state))

            events.put(("complete", result))
            logger.info("Analysis completed. Conversation ID: %s", conversation_id)
        except Exception as error:
            logger.exception("Analysis failed. Conversation ID: %s. Error: %s", conversation_id, error)
            try:
                save_message(conversation_id, "assistant", "Unable to complete the IPL analysis. Please try again.")
            except Exception as storage_error:
                logger.exception("Unable to save error message for conversation %s: %s", conversation_id, storage_error)
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
        raise RuntimeError(f"Unable to start the analysis stream for conversation '{conversation_id}': {error}") from error
