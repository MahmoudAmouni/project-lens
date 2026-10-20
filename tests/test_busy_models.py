"""A busy server (5xx, e.g. Gemini 503 "overloaded") switches to another model, and errors name the right provider."""

import groq
import pytest

import AI.llm_client as llm_module
from AI.errors import AIRateLimitedError, AIUnavailableError
from AI.llm_client import LLMClient, LLMReply
from AI.llm_helpers import providers_of, rate_limit_message, wait_text
from tests.test_llm_client import REQUEST, api_error

OK = LLMReply(content="ok")


class ScriptedClient(LLMClient):
    def __init__(self, script: list, model: str = "main-model", fallback_model: str = "backup-model"):
        super().__init__(api_key="test-key", model=model, fallback_model=fallback_model)
        self.script = list(script)
        self.models_used: list[str] = []

    def _call(self, model, messages, tools, tool_choice, json_mode=False):
        self.models_used.append(model)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture(autouse=True)
def no_sleeping(monkeypatch):
    monkeypatch.setattr(llm_module.time, "sleep", lambda seconds: None)


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_a_busy_model_switches_to_the_backup(status):
    client = ScriptedClient([api_error(groq.APIStatusError, status), OK])
    assert client.complete([], []) is OK
    assert client.models_used == ["main-model", "backup-model"]


def test_when_every_model_is_busy_the_message_says_busy_not_rate_limit():
    client = ScriptedClient([api_error(groq.APIStatusError, 503), api_error(groq.APIStatusError, 503)])
    client.max_wait_seconds = 5  # less than the busy rest, so it gives up instead of waiting
    with pytest.raises(AIRateLimitedError, match="Groq is busy right now"):
        client.complete([], [])


def test_a_busy_gemini_model_is_named_as_gemini():
    busy = api_error(groq.APIStatusError, 503)
    client = ScriptedClient([busy, busy], model="gemini-3.5-flash", fallback_model="gemini-3.5-flash-lite")
    client.max_wait_seconds = 5
    with pytest.raises(AIRateLimitedError, match="^Gemini is busy"):
        client.complete([], [])


def test_other_client_errors_name_the_provider_and_status():
    client = ScriptedClient([api_error(groq.APIStatusError, 403)], model="gemini-3.5-flash", fallback_model="")
    with pytest.raises(AIUnavailableError, match=r"Gemini refused the request \(error 403\)"):
        client.complete([], [])


def test_a_lost_connection_names_the_provider():
    lost = groq.APIConnectionError(request=REQUEST)
    client = ScriptedClient([lost, lost, lost], model="gemini-3.5-flash", fallback_model="")
    with pytest.raises(AIUnavailableError, match="Gemini is unreachable"):
        client.complete([], [])


def test_a_rate_limit_after_a_busy_server_gives_the_rate_limit_message():
    limit = api_error(groq.RateLimitError, 429, headers={"retry-after": "600"})
    client = ScriptedClient([api_error(groq.APIStatusError, 503), limit])
    client.max_wait_seconds = 5
    with pytest.raises(AIRateLimitedError, match="Groq is busy"):  # the main model is still resting as busy
        client.complete([], [])


@pytest.mark.parametrize(
    ("seconds", "text"),
    [(30, "about 1 minute"), (60, "about 1 minute"), (600, "about 10 minutes"), (3 * 3600, "about 3 hours"),
     (3600, "about 60 minutes"), (5400, "about 2 hours")],
)  # fmt: skip
def test_wait_times_read_naturally(seconds, text):
    assert wait_text(seconds) == text


def test_messages_name_every_provider_that_was_tried():
    assert providers_of(["openai/gpt-oss-120b", "gemini-3.5-flash"]) == "Groq and Gemini"
    assert providers_of([]) == "Groq"
    message = rate_limit_message(True, 60, ["openai/gpt-oss-120b", "gemini-3.5-flash"])
    assert message == "The free daily limit of Groq and Gemini is used up for all models. Try again in about 1 minute."
