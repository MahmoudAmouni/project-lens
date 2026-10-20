"""Small helpers for llm_client.py: model lists from .env, which key a model uses, and reading API errors."""

import re

import groq

from AI.gemini_client import is_gemini

DEFAULT_WAIT_SECONDS = 5.0
RETRY_IN_PATTERN = re.compile(r"retry in ([\d.]+)s", re.IGNORECASE)


def model_names(text: str | None) -> list[str]:
    """ "a, b" -> ["a", "b"]"""
    return [name.strip() for name in (text or "").split(",") if name.strip()]


def key_name(model: str) -> str:
    return "GEMINI_API_KEY" if is_gemini(model) else "GROQ_API_KEY"


def retry_after_seconds(error: groq.RateLimitError) -> float:
    """Seconds to wait: Groq's retry-after header, Gemini's "retry in 23.5s" text, or a default."""
    try:
        header = error.response.headers.get("retry-after")
        if header is not None:
            return float(header) + 0.5
    except (AttributeError, TypeError, ValueError):
        return DEFAULT_WAIT_SECONDS
    found = RETRY_IN_PATTERN.search(str(error))
    return float(found.group(1)) + 0.5 if found else DEFAULT_WAIT_SECONDS


def rate_limit_message(daily_limit_hit: bool, wait_seconds: float) -> str:
    """What the user reads when every model is rate limited for longer than we may wait."""
    if daily_limit_hit:
        minutes = max(1, round(wait_seconds / 60))
        return f"Groq's free daily token limit is used up for all models. Try again in about {minutes} minutes."
    return "Groq's free rate limit is reached. Wait a minute and try again."


def tool_use_failure(error: groq.BadRequestError) -> str | None:
    """Groq answers 400 "tool_use_failed" or "output_parse_failed" when the model writes a broken reply."""
    body = error.body if isinstance(error.body, dict) else {}
    details = body["error"] if isinstance(body.get("error"), dict) else body
    if details.get("code") not in ("tool_use_failed", "output_parse_failed"):
        return None
    reason = str(details.get("message") or "invalid tool call")
    generated = str(details.get("failed_generation") or "")[:600]
    return f"{reason} You wrote: {generated}" if generated else reason
