
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

import ast
import json

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


# Initialise and cache the configured language model.
@lru_cache(maxsize=8)
def get_llm(model: str = "gemini-3.5-flash-lite", provider: str = "google_genai", temperature: float = 0.0) -> Any:
    try:
        print(f"[LLM] Initialising {model} through {provider}.")
        if provider == "google_genai" and not os.getenv("GOOGLE_API_KEY"):
            raise EnvironmentError("GROQ_API_KEY is missing from the project environment.")
        return init_chat_model(model=model, model_provider=provider,) # temperature=temperature)
    except Exception as error:
        raise RuntimeError(f"LLM initialisation failed for model '{model}' and provider '{provider}': {error}") from error


# Load a prompt using a path relative to the project root.
def load_prompt(relative_path: str) -> str:
    prompt_path = ROOT_DIR / relative_path
    try:
        print(f"[PROMPT] Loading {prompt_path}.")
        if not prompt_path.is_file():
            raise FileNotFoundError(f"Prompt file does not exist: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")
    except Exception as error:
        raise RuntimeError(f"Unable to load prompt '{prompt_path}': {error}") from error


# Convert the model response into plain text, including block-based responses.
def extract_response_text(response: Any) -> str:
    try:
        content = response.content
        if isinstance(content, str):
            response_text = content
        elif isinstance(content, list):
            response_text = "".join(item.get("text", "") if isinstance(item, dict) else str(item) for item in content)
        else:
            response_text = str(content)
        response_text = response_text.strip()
        if not response_text:
            raise ValueError("The model returned an empty response.")
        return response_text
    except Exception as error:
        raise RuntimeError(f"Unable to extract text from the LLM response: {error}") from error


# Invoke the LLM with a system prompt and a user prompt.
def invoke_llm(llm: Any, system_prompt: str, user_prompt: str, stage: str) -> str:
    try:
        print(f"[LLM] Executing stage: {stage}.")
        response = llm.invoke([
            SystemMessage(content=system_prompt), 
            HumanMessage(content=user_prompt)
        ])
        response_text = extract_response_text(response)
        print(f"[LLM] Stage '{stage}' completed. Response length: {len(response_text)} characters.")
        return response_text
    except Exception as error:
        raise RuntimeError(f"LLM invocation failed during '{stage}': {error}") from error


# Parse a JSON or Python-literal response from an LLM.
def parse_structured_response(response_text: str, stage: str) -> Any:
    try:
        cleaned_text = response_text.strip()
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError:
            return ast.literal_eval(cleaned_text)
    except Exception as error:
        raise ValueError(f"{stage} returned an invalid structured response: {response_text[:1000]}. Error: {error}") from error
