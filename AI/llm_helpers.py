"""Small helpers for llm_client.py: model lists from .env, which key a model uses, and reading API errors."""

import re

import groq

from AI.errors import AIUnavailableError, RequestTooLargeError
from AI.gemini_client import is_gemini
from AI.openrouter_client import is_openrouter

DEFAULT_WAIT_SECONDS = 5.0
RETRY_IN_PATTERN = re.compile(r"retry in ([\d.]+)s", re.IGNORECASE)


def model_names(text: str | None) -> list[str]:
    """ "a, b" -> ["a", "b"]"""
    return [name.strip() for name in (text or "").split(",") if name.strip()]


def key_name(model: str) -> str:
    return f"{provider_name(model).upper()}_API_KEY"


def provider_name(model: str) -> str:
    return "Gemini" if is_gemini(model) else "OpenRouter" if is_openrouter(model) else "Groq"


def is_daily_limit(error: groq.RateLimitError) -> bool:
    """Groq says "per day", Gemini "PerDay", OpenRouter "free-models-per-day"."""
    return any(mark in str(error) for mark in ("per day", "PerDay", "per-day"))


def providers_of(models: list[str]) -> str:
    """ "Groq", "Gemini" or "Groq and Gemini": who the user is waiting for."""
    names = list(dict.fromkeys(provider_name(model) for model in models)) or ["Groq"]
    return " and ".join(names)


def wait_text(seconds: float) -> str:
    """ "about 1 minute", "about 25 minutes", "about 3 hours"."""
    minutes = max(1, round(seconds / 60))
    if minutes >= 90:
        hours = round(minutes / 60)
        return f"about {hours} hour{'s' if hours != 1 else ''}"
    return f"about {minutes} minute{'s' if minutes != 1 else ''}"


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


def rate_limit_message(daily_limit_hit: bool, wait_seconds: float, models: list[str], busy: bool = False) -> str:
    """What the user reads when no model can answer within the time we may wait."""
    providers = providers_of(models)
    if busy:
        return f"{providers} is busy right now (server overloaded). Try again in a minute."
    if daily_limit_hit:
        return f"The free daily limit of {providers} is used up for all models. Try again in {wait_text(wait_seconds)}."
    return f"The free rate limit of {providers} is reached. Wait a minute and try again."


def status_problem(status_code: int, model: str) -> Exception | None:
    """The error to raise for an HTTP error, or None for a busy server (5xx): then another model is tried."""
    if status_code == 413:
        return RequestTooLargeError("The request is larger than Groq's free tier allows.")
    if status_code < 500:
        return AIUnavailableError(f"{provider_name(model)} refused the request (error {status_code}).")
    return None


def request_options(
    model: str, tools: list[dict], tool_choice: str | dict, json_mode: bool, max_tokens: int | None, effort: str
) -> dict:
    """The extra settings each model family needs for one chat request."""
    options: dict = {"tools": tools, "tool_choice": tool_choice} if tools else {}
    if not is_gemini(model):  # 0 = the same answer to the same question; Gemini 3 is made for its default (1.0)
        options["temperature"] = 0
    if json_mode:
        options["response_format"] = {"type": "json_object"}
    if is_gemini(model) and isinstance(tool_choice, dict) and tools:
        options["tool_choice"] = "required"  # Gemini wants "required" to force the one tool given
    if model.startswith("openai/gpt-oss"):
        options["reasoning_effort"] = effort
    elif model.startswith("qwen/") and not is_openrouter(model):
        options["reasoning_format"] = "hidden"  # keep <think> text out of the answer
    if max_tokens:
        options["max_tokens"] = max_tokens
    return options


def tool_use_failure(error: groq.BadRequestError) -> str | None:
    """Groq answers 400 "tool_use_failed" or "output_parse_failed" when the model writes a broken reply."""
    body = error.body if isinstance(error.body, dict) else {}
    details = body["error"] if isinstance(body.get("error"), dict) else body
    if details.get("code") not in ("tool_use_failed", "output_parse_failed"):
        return None
    reason = str(details.get("message") or "invalid tool call")
    generated = str(details.get("failed_generation") or "")[:600]
    return f"{reason} You wrote: {generated}" if generated else reason
