"""OpenRouter's free models as more pickable backups: path, routing, names and limits (no API calls)."""

import time

import groq
import httpx

from AI.llm_client import LLMClient
from AI.llm_helpers import is_daily_limit, key_name, provider_name, request_options
from AI.openrouter_client import fix_openrouter_path, is_openrouter
from AI.usage_tracker import UsageTracker
from tests.test_gemini_model import QUESTION, fake_client, rate_limit_error

FREE_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"


def openrouter_llm(tmp_path, **options) -> LLMClient:
    usage = UsageTracker(str(tmp_path / "usage.json"))
    return LLMClient(
        api_key="test-key", model="groq-a", fallback_model="groq-b", usage=usage,
        gemini_api_key="test-gemini-key", gemini_model="gemini-3.5-flash",
        openrouter_api_key="test-openrouter-key", openrouter_model=FREE_MODEL, **options,
    )  # fmt: skip


def test_the_path_is_fixed_for_openrouter():
    request = httpx.Request("POST", "https://openrouter.ai/api/openai/v1/chat/completions")
    fix_openrouter_path(request)
    assert request.url.path == "/api/v1/chat/completions"


def test_free_models_are_named_and_keyed_as_openrouter():
    assert is_openrouter(FREE_MODEL) and not is_openrouter("openai/gpt-oss-120b")
    assert provider_name(FREE_MODEL) == "OpenRouter"
    assert key_name(FREE_MODEL) == "OPENROUTER_API_KEY"
    assert key_name("gemini-3.5-flash") == "GEMINI_API_KEY" and key_name("openai/gpt-oss-120b") == "GROQ_API_KEY"


def test_groq_only_settings_are_not_sent_to_openrouter():
    options = request_options("qwen/qwen3-coder:free", [], "auto", False, None, "medium")
    assert "reasoning_format" not in options and options["temperature"] == 0


def test_openrouter_is_a_choice_after_gemini(tmp_path):
    llm = openrouter_llm(tmp_path)
    assert llm.configured_models == ["groq-a", "groq-b", "gemini-3.5-flash", FREE_MODEL]
    assert llm.models == ["groq-a", "groq-b"]
    llm.prefer(FREE_MODEL)
    assert llm.models == [FREE_MODEL, "groq-a", "groq-b"]


def test_no_key_means_no_openrouter_models(tmp_path):
    llm = LLMClient(api_key="test-key", model="groq-a", openrouter_api_key="", openrouter_model=FREE_MODEL)
    assert llm.openrouter_models == [] and llm.openrouter_client is None


def test_a_picked_openrouter_model_uses_the_openrouter_client(tmp_path):
    llm = openrouter_llm(tmp_path)
    llm.client, groq_calls = fake_client()
    llm.openrouter_client, openrouter_calls = fake_client()
    llm.prefer(FREE_MODEL)
    assert llm.complete(QUESTION, []).model == FREE_MODEL
    assert groq_calls.sent == [] and len(openrouter_calls.sent) == 1


def test_openrouter_takes_over_when_groq_and_gemini_are_limited(tmp_path):
    llm = openrouter_llm(tmp_path)
    llm.client, groq_calls = fake_client()
    llm.gemini_client, gemini_calls = fake_client()
    llm.openrouter_client, openrouter_calls = fake_client()

    def limited(**options):
        raise rate_limit_error()

    groq_calls.create = limited
    gemini_calls.create = limited
    assert llm.complete(QUESTION, []).model == FREE_MODEL
    assert llm.limited_until["gemini-3.5-flash"] > time.monotonic()


def test_openrouter_daily_limit_is_recognised():
    response = httpx.Response(429, request=httpx.Request("POST", "https://x.test"))
    error = groq.RateLimitError("Rate limit exceeded: free-models-per-day.", response=response, body=None)
    assert is_daily_limit(error)


def test_openrouter_counts_requests_per_day_not_tokens(tmp_path):
    llm = openrouter_llm(tmp_path)
    status = llm.usage.snapshot(FREE_MODEL)
    assert status["daily_token_limit"] is None and status["daily_request_limit"] == 50
