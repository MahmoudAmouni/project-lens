"""OpenRouter (free models such as NVIDIA Nemotron and MiniMax), reached with the same groq SDK as Groq.

The groq SDK sends requests to <base_url>/openai/v1/chat/completions, while OpenRouter expects
https://openrouter.ai/api/v1/chat/completions. A small hook fixes the path, so errors, tool calls and replies
look exactly like Groq's and LLMClient handles them the same way.
"""

import groq
import httpx

OPENROUTER_BASE_URL = "https://openrouter.ai/api"
DAILY_FREE_REQUESTS = 50  # OpenRouter's free models without bought credits (1,000 after buying $10)


def is_openrouter(model: str) -> bool:
    """OpenRouter's free models end with ":free" (for example "nvidia/nemotron-3-ultra-550b-a55b:free")."""
    return model.endswith(":free")


def fix_openrouter_path(request: httpx.Request) -> None:
    request.url = request.url.copy_with(path=request.url.path.replace("/api/openai/v1/", "/api/v1/"))


def make_openrouter_client(api_key: str, timeout_seconds: float) -> groq.Groq:
    http_client = httpx.Client(event_hooks={"request": [fix_openrouter_path]}, timeout=timeout_seconds)
    return groq.Groq(api_key=api_key, base_url=OPENROUTER_BASE_URL, max_retries=0, http_client=http_client)
