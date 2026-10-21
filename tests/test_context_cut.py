"""Old tool results stay whole for Gemini and OpenRouter (big limits) and are only cut for Groq's small free tier."""

from pathlib import Path

import pytest

from AI.agent import Agent
from AI.context_budget import BIG_REQUEST_TOKEN_BUDGET, REQUEST_TOKEN_BUDGET, SHORTENED, request_budget
from AI.llm_client import LLMClient
from AI.usage_tracker import UsageTracker
from Server.ingestion.folder_loader import load_folder
from tests.fake_llm import FakeLLM, call, tool_reply

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_docs"


@pytest.fixture(scope="module")
def documents():
    return load_folder(SAMPLE_DIR).documents


class BigLimitLLM(FakeLLM):
    """A fake whose next model is a backup provider (like Gemini), as LLMClient reports it."""

    backup_models = ["gemini-3.5-flash"]

    def pick_model(self):
        return "gemini-3.5-flash", 0.0


def real_client(tmp_path) -> LLMClient:
    return LLMClient(
        api_key="test-key", model="groq-a", usage=UsageTracker(str(tmp_path / "usage.json")),
        gemini_api_key="test-gemini-key", gemini_model="gemini-3.5-flash",
    )  # fmt: skip


def test_the_budget_follows_the_model_about_to_answer(tmp_path):
    llm = real_client(tmp_path)
    assert request_budget(llm) == REQUEST_TOKEN_BUDGET  # Groq goes first
    llm.prefer("gemini-3.5-flash")
    assert request_budget(llm) == BIG_REQUEST_TOKEN_BUDGET
    assert request_budget(FakeLLM([])) == REQUEST_TOKEN_BUDGET  # unknown clients get the safe small budget


def script() -> list:
    read = call("read_document", {"document": "Technical_Specifications.pdf", "start_page": 1, "end_page": 10})
    second = call("read_document", {"document": "Contract_A.pdf", "start_page": 4, "end_page": 4}, call_id="second")
    source = {"document": "Contract_A.pdf", "page": 4}
    submit = call("submit_answer", {"answer": "Retention is **5%**.", "sources": [source]})
    return [tool_reply(read), tool_reply(second), tool_reply(submit)]


def first_tool_result(llm: FakeLLM) -> str:
    return next(m["content"] for m in llm.requests[-1]["messages"] if m["role"] == "tool")


def test_old_results_stay_whole_for_a_big_limit_model(documents):
    llm = BigLimitLLM(script())
    Agent(llm, documents).ask("What is the retention?")
    assert not first_tool_result(llm).endswith(SHORTENED)


def test_old_results_are_still_cut_for_groq(documents):
    llm = FakeLLM(script())
    Agent(llm, documents).ask("What is the retention?")
    assert first_tool_result(llm).endswith(SHORTENED)
