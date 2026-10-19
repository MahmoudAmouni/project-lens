"""Keep every request under Groq's free-tier limit (~8,000 tokens per minute, and one request can't be bigger).

Tool results the model has already read are shortened first; if the request is still too big, the
longest results are cut further until it fits.
"""

import json

OLD_RESULT_CHARS = 1_500  # results from earlier rounds, once the model has read them
REQUEST_TOKEN_BUDGET = 5_500  # leaves room for the reply inside the 8,000 tokens per minute
MIN_RESULT_CHARS = 300
CHARS_PER_TOKEN = 3.2  # rough and on the safe side (JSON and Arabic use more tokens per character)
SHORTENED = ' ..."[shortened]"'


def estimate_tokens(messages: list[dict], tools: list[dict]) -> int:
    text = json.dumps(messages, ensure_ascii=False) + json.dumps(tools)
    return int(len(text) / CHARS_PER_TOKEN)


def shorten(message: dict, max_chars: int) -> None:
    if len(message["content"]) > max_chars:
        message["content"] = message["content"][:max_chars] + SHORTENED


def shorten_old_results(messages: list[dict]) -> None:
    """Cut tool results from earlier rounds; the latest round stays whole."""
    last_assistant = max((i for i, m in enumerate(messages) if m["role"] == "assistant"), default=-1)
    for message in messages[:last_assistant]:
        if message["role"] == "tool":
            shorten(message, OLD_RESULT_CHARS)


def fit_to_budget(messages: list[dict], tools: list[dict], budget: int = REQUEST_TOKEN_BUDGET) -> None:
    """Halve the longest tool results until the request fits the budget."""
    while estimate_tokens(messages, tools) > budget:
        results = [m for m in messages if m["role"] == "tool" and len(m["content"]) > MIN_RESULT_CHARS + 50]
        if not results:
            return
        longest = max(results, key=lambda m: len(m["content"]))
        shorten(longest, max(MIN_RESULT_CHARS, len(longest["content"]) // 2))
