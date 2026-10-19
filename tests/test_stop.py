"""The Stop button: a stopped question ends at the next check and makes no more AI calls (no API cost)."""

import time
from pathlib import Path

import groq
import httpx
import pytest

from AI.agent import Agent
from AI.errors import QuestionStopped
from AI.llm_client import LLMClient
from AI.router import Router
from Server.ingestion.folder_loader import load_folder
from tests.fake_llm import FakeLLM, call, tool_reply

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_docs"
READ = tool_reply(call("read_document", {"document": "Contract_A.pdf", "start_page": 1, "end_page": 1}))


@pytest.fixture(scope="module")
def documents():
    return load_folder(SAMPLE_DIR).documents


def test_stop_before_starting_makes_no_ai_call(documents):
    llm = FakeLLM([READ])
    with pytest.raises(QuestionStopped):
        Agent(llm, documents).ask("Summarize the contract", should_stop=lambda: True)
    assert llm.requests == []


def test_stop_between_rounds_ends_before_the_next_call(documents):
    llm = FakeLLM([READ, READ, READ])
    stop_after_first_call = lambda: len(llm.requests) >= 1  # noqa: E731
    with pytest.raises(QuestionStopped):
        Agent(llm, documents).ask("Summarize the contract", should_stop=stop_after_first_call)
    assert len(llm.requests) == 1


def test_stop_check_is_cleared_after_the_question(documents):
    agent = Agent(FakeLLM([READ]), documents)
    with pytest.raises(QuestionStopped):
        agent.ask("Summarize the contract", should_stop=lambda: True)
    assert agent.should_stop is None and agent.llm.should_stop is None


class StoppableRouterLLM:
    should_stop = None

    def complete_json(self, messages):
        raise QuestionStopped("stopped while routing")


def test_router_does_not_hide_a_stop_behind_its_fail_safe():
    with pytest.raises(QuestionStopped):
        Router(StoppableRouterLLM()).route("shu l items yalli aktar men malyon?")


def test_stop_ends_a_long_rate_limit_wait_at_once(monkeypatch):
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    limited = groq.RateLimitError(
        "limit", response=httpx.Response(429, request=request, headers={"retry-after": "60"}), body=None
    )
    client = LLMClient(api_key="test-key", model="only-model")
    monkeypatch.setattr(client, "_call", lambda *args: (_ for _ in ()).throw(limited))
    pressed_at = time.monotonic() + 0.5
    client.should_stop = lambda: time.monotonic() > pressed_at
    start = time.monotonic()
    with pytest.raises(QuestionStopped):
        client.complete([], [])
    assert time.monotonic() - start < 3  # not the 60 seconds Groq asked for
