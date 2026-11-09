
import json
from typing import Any

from src.utils.llm_utils import get_llm, invoke_llm, load_prompt, parse_structured_response


# Resolve the current question using recent conversation history.
def resolve_conversation_context(user_question: str, conversation_history: list[dict[str, Any]], conversation_context: dict[str, Any]) -> dict[str, Any]:
    try:
        print("[CONVERSATION AGENT] Resolving conversational context.")

        if not conversation_history and not conversation_context:
            print("[CONVERSATION AGENT] New conversation detected. Skipping context resolution.")
            return {"standalone_question": user_question, "needs_clarification": False, "clarification_question": "", "reason": "New conversation."}

        recent_history = conversation_history[-8:]
        compact_context = json.dumps(conversation_context, default=str, separators=(",", ":"))[:3000]
        history_json = json.dumps(recent_history, default=str, separators=(",", ":"))

        system_prompt = load_prompt("./src/prompts/conversation_context_system_prompt.txt")
        user_prompt = load_prompt("./src/prompts/conversation_context_user_prompt.txt").format(user_question=user_question, conversation_history=history_json, conversation_context=compact_context)

        print(f"[CONVERSATION AGENT] Context prompt size: {len(user_prompt)} characters.")

        llm = get_llm()
        response = invoke_llm(llm, system_prompt, user_prompt, "conversation_context_resolution")
        result = parse_structured_response(response, "Conversation Context Agent")

        required_fields = {"standalone_question", "needs_clarification", "clarification_question", "reason"}
        if not isinstance(result, dict):
            raise ValueError("Conversation Context Agent must return a JSON object.")
        missing_fields = required_fields - set(result)
        if missing_fields:
            raise ValueError(f"Conversation context response is missing fields: {sorted(missing_fields)}.")
        if not isinstance(result["standalone_question"], str) or not result["standalone_question"].strip():
            raise ValueError("The standalone question cannot be empty.")
        if not isinstance(result["needs_clarification"], bool):
            raise ValueError("'needs_clarification' must be a boolean.")
        if result["needs_clarification"] and not result["clarification_question"].strip():
            raise ValueError("A clarification question is required when clarification is needed.")

        result["standalone_question"] = result["standalone_question"].strip()
        result["clarification_question"] = result["clarification_question"].strip()
        print(f"[CONVERSATION AGENT] Resolved question: {result['standalone_question']}.")
        return result
    except Exception as error:
        raise RuntimeError(f"Unable to resolve conversational context for '{user_question}': {error}") from error
