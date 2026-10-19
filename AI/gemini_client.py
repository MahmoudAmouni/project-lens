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
