"""Gemini as one more pickable model: routing, its request-based limits and its errors (no API calls)."""

import time
from types import SimpleNamespace

import groq
import httpx
import pytest

from AI.errors import AIUnavailableError
from AI.gemini_client import fix_gemini_path
from AI.llm_client import LLMClient
from AI.llm_helpers import retry_after_seconds
from AI.usage_tracker import UsageTracker

GEMINI_QUOTA_ERROR = (
    "Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, "
    "limit: 20, model: gemini-2.5-flash [quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier] "
    "Please retry in 23.5s."
)


class FakeCompletions:
    """Stands in for client.chat.completions; records what was sent."""

    def __init__(self):
        self.sent: list[dict] = []
        self.with_raw_response = self

    def create(self, **options):
        self.sent.append(options)
        message = SimpleNamespace(content="ok", tool_calls=None)
        reply = SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=SimpleNamespace(total_tokens=42))
        return SimpleNamespace(headers={}, parse=lambda: reply)


def fake_client() -> tuple[SimpleNamespace, FakeCompletions]:
    completions = FakeCompletions()
    return SimpleNamespace(chat=SimpleNamespace(completions=completions)), completions


def gemini_llm(tmp_path, **options) -> LLMClient:
    usage = UsageTracker(str(tmp_path / "usage.json"))
    return LLMClient(
        api_key="test-key", model="groq-a", fallback_model="groq-b", usage=usage,
        gemini_api_key="test-gemini-key", gemini_model="gemini-2.5-flash", gemini_daily_requests=250, **options,
    )  # fmt: skip


def test_the_path_is_fixed_for_gemini_openai_endpoint():
    request = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/openai/v1/chat/completions")
    fix_gemini_path(request)
    assert request.url.path == "/v1beta/openai/chat/completions"


def test_gemini_is_a_choice_and_not_in_the_normal_order(tmp_path):
    llm = gemini_llm(tmp_path)
    assert llm.configured_models == ["groq-a", "groq-b", "gemini-2.5-flash"]
    assert llm.models == ["groq-a", "groq-b"]
    llm.prefer("gemini-2.5-flash")
    assert llm.models == ["gemini-2.5-flash", "groq-a", "groq-b"]  # the Groq models back it up
    llm.prefer("groq-b")
    assert llm.models == ["groq-b", "groq-a"]


def rate_limit_error() -> groq.RateLimitError:
    response = httpx.Response(429, headers={"retry-after": "600"}, request=httpx.Request("POST", "https://x.test"))
    return groq.RateLimitError("Rate limit reached", response=response, body=None)


QUESTION = [{"role": "user", "content": "hi"}]


def test_groq_answers_while_it_is_free_even_with_a_gemini_key(tmp_path):
    llm = gemini_llm(tmp_path)
    llm.client, groq_calls = fake_client()
    llm.gemini_client, gemini_calls = fake_client()
    llm.limited_until["groq-a"] = time.monotonic() - 5  # a limit that has already ended
    assert llm.complete(QUESTION, []).model == "groq-a"
    assert gemini_calls.sent == []


def test_gemini_takes_over_when_every_groq_model_is_rate_limited(tmp_path):
    llm = gemini_llm(tmp_path)
    llm.client, groq_calls = fake_client()
    llm.gemini_client, gemini_calls = fake_client()

    def limited(**options):
        groq_calls.sent.append(options)
        raise rate_limit_error()

    groq_calls.create = limited
    assert llm.complete(QUESTION, []).model == "gemini-2.5-flash"  # no 10-minute wait for Groq
    assert [call["model"] for call in groq_calls.sent] == ["groq-a", "groq-b"]
    assert len(gemini_calls.sent) == 1


def test_without_a_gemini_key_there_is_no_gemini_choice(tmp_path):
    llm = LLMClient(api_key="test-key", model="groq-a", gemini_api_key="", gemini_model="gemini-2.5-flash")
    assert llm.configured_models == ["groq-a"]


def test_gemini_calls_go_to_gemini_and_count_one_request(tmp_path):
    llm = gemini_llm(tmp_path)
    llm.client, groq_calls = fake_client()
    llm.gemini_client, gemini_calls = fake_client()
    llm.prefer("gemini-2.5-flash")
    forced = {"type": "function", "function": {"name": "submit_answer"}}
    tool = [{"type": "function", "function": {"name": "submit_answer"}}]
    assert llm.complete([{"role": "user", "content": "hi"}], tool, tool_choice=forced).model == "gemini-2.5-flash"
    assert groq_calls.sent == [] and gemini_calls.sent[0]["tool_choice"] == "required"
    left = llm.usage.snapshot("gemini-2.5-flash")
    assert left["requests_left_today"] == 249 and left["daily_request_limit"] == 250
    assert left["daily_token_limit"] is None and left["tokens_used_today"] == 42


def test_gemini_quota_error_gives_the_real_daily_limit(tmp_path):
    usage = UsageTracker(str(tmp_path / "usage.json"))
    usage.count_requests("gemini-2.5-flash", 250)
    usage.record_limit("gemini-2.5-flash", GEMINI_QUOTA_ERROR, wait_seconds=24)
    left = usage.snapshot("gemini-2.5-flash")
    assert left["daily_request_limit"] == 20 and left["requests_left_today"] == 0


def test_gemini_retry_time_is_read_from_the_message():
    response = httpx.Response(429, request=httpx.Request("POST", "https://example.test"))
    error = groq.RateLimitError(GEMINI_QUOTA_ERROR, response=response, body=None)
    assert retry_after_seconds(error) == 24.0


def test_wrong_gemini_key_names_the_gemini_key(tmp_path):
    llm = gemini_llm(tmp_path)
    response = httpx.Response(400, request=httpx.Request("POST", "https://example.test"))

    def refuse(**options):
        raise groq.BadRequestError("API key not valid. Please pass a valid API key.", response=response, body=None)

    llm.gemini_client, completions = fake_client()
    completions.create = refuse
    llm.prefer("gemini-2.5-flash")
    with pytest.raises(AIUnavailableError, match="GEMINI_API_KEY"):
        llm.complete([{"role": "user", "content": "hi"}], [])
