"""Google Gemini, reached through its OpenAI-style endpoint with the same groq SDK the rest of the app uses.

The groq SDK sends requests to <base_url>/openai/v1/chat/completions, while Gemini expects
<base_url>/openai/chat/completions. A small hook fixes the path, so errors, tool calls and replies
look exactly like Groq's and LLMClient handles both the same way.
"""

import groq
import httpx

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def is_gemini(model: str) -> bool:
    return model.startswith("gemini-") or model.startswith("gemma-")


def fix_gemini_path(request: httpx.Request) -> None:
    request.url = request.url.copy_with(path=request.url.path.replace("/openai/v1/", "/openai/"))


def make_gemini_client(api_key: str, timeout_seconds: float) -> groq.Groq:
    http_client = httpx.Client(event_hooks={"request": [fix_gemini_path]}, timeout=timeout_seconds)
    return groq.Groq(api_key=api_key, base_url=GEMINI_BASE_URL, max_retries=0, http_client=http_client)


def extra_content_of(tool_call) -> dict | None:
    """Gemini's `extra_content` (the thought signature) on a returned tool call; None for Groq."""
    return (getattr(tool_call, "model_extra", None) or {}).get("extra_content")


# Google's documented placeholder for tool calls that another model made (Gemini did not sign them).
PLACEHOLDER_SIGNATURE = {"google": {"thought_signature": "skip_thought_signature_validator"}}


def messages_for_model(messages: list[dict], gemini: bool) -> list[dict]:
    """Gemini 3 needs the thought signature of every earlier tool call back (`extra_content`); calls a Groq model
    made get the placeholder. Groq refuses that unknown field, so it is removed before a Groq call."""
    fixed = []
    for message in messages:
        if message.get("tool_calls"):
            calls = [
                {**call, "extra_content": call.get("extra_content") or PLACEHOLDER_SIGNATURE}
                if gemini
                else {key: value for key, value in call.items() if key != "extra_content"}
                for call in message["tool_calls"]
            ]
            message = {**message, "tool_calls": calls}
        fixed.append(message)
    return fixed
