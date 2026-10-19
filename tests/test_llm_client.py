"""Groq client error handling, with fake errors (no API calls)."""

import groq
import httpx
import pytest

import AI.llm_client as llm_module
from AI.errors import AIRateLimitedError, AIUnavailableError, RequestTooLargeError, ToolCallFormatError
from AI.llm_client import LLMClient, LLMReply

REQUEST = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")


def api_error(error_class, status: int, body: dict | None = None, headers: dict | None = None):
    response = httpx.Response(status, request=REQUEST, headers=headers or {})
    return error_class("error", response=response, body=body)


class ScriptedClient(LLMClient):
    """LLMClient whose Groq call raises or returns scripted items, recording which model was used."""

    def __init__(self, script: list):
        super().__init__(api_key="test-key", model="main-model", fallback_model="backup-model")
        self.script = list(script)
        self.models_used: list[str] = []

    def _call(self, model, messages, tools, tool_choice):
        self.models_used.append(model)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture(autouse=True)
def no_sleeping(monkeypatch):
    monkeypatch.setattr(llm_module.time, "sleep", lambda seconds: None)


OK = LLMReply(content="ok")


def test_rate_limit_switches_to_the_backup_model():
    client = ScriptedClient([api_error(groq.RateLimitError, 429, headers={"retry-after": "10"}), OK])
    assert client.complete([], []) is OK
    assert client.models_used == ["main-model", "backup-model"]


def test_many_short_rate_limits_are_waited_out_not_counted_as_failures():
    limits = [api_error(groq.RateLimitError, 429, headers={"retry-after": "0"}) for _ in range(8)]
    client = ScriptedClient([*limits, OK])
    assert client.complete([], []) is OK


def test_removed_model_is_dropped_and_backup_is_used():
    client = ScriptedClient([api_error(groq.NotFoundError, 404), OK])
    assert client.complete([], []) is OK
    assert client.models == ["backup-model"]


def test_broken_tool_call_becomes_tool_call_format_error():
    body = {"error": {"code": "tool_use_failed", "message": "bad schema", "failed_generation": '{"x": nul'}}
    client = ScriptedClient([api_error(groq.BadRequestError, 400, body=body)])
    with pytest.raises(ToolCallFormatError, match="bad schema"):
        client.complete([], [])


def test_request_too_large_is_its_own_error():
    client = ScriptedClient([api_error(groq.APIStatusError, 413)])
    with pytest.raises(RequestTooLargeError):
        client.complete([], [])


def test_wrong_api_key_gives_clear_message():
    client = ScriptedClient([api_error(groq.AuthenticationError, 401)])
    with pytest.raises(AIUnavailableError, match="GROQ_API_KEY"):
        client.complete([], [])


def test_missing_api_key_gives_clear_message():
    with pytest.raises(AIUnavailableError, match="Add your GROQ_API_KEY"):
        LLMClient(api_key="", model="m")


def test_several_backup_models_are_tried_in_turn():
    client = LLMClient(api_key="test-key", model="a", fallback_model="b, c")
    assert client.models == ["a", "b", "c"]


def test_daily_limit_gives_a_clear_message():
    error = groq.RateLimitError(
        "Rate limit reached on tokens per day (TPD)",
        response=httpx.Response(429, request=REQUEST, headers={"retry-after": "600"}),
        body=None,
    )
    client = ScriptedClient([error, error])
    with pytest.raises(AIRateLimitedError, match="daily token limit"):
        client.complete([], [])
