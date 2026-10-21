"""A tool name with a prefix ("functions.submit_answer") still runs the tool, so a finished answer is never lost."""

from pathlib import Path

import pytest

from AI.agent import Agent
from AI.llm_reply import LLMReply, ToolCall
from Server.ingestion.folder_loader import load_folder
from tests.fake_llm import FakeLLM, call

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_docs"


@pytest.mark.parametrize(
    "name", ["functions.submit_answer", "default_api.submit_answer", "tools.submit_answer", " submit_answer "]
)
def test_prefixes_are_removed(name):
    assert ToolCall("1", name, "{}").name == "submit_answer"


def test_a_plain_name_is_unchanged():
    assert ToolCall("1", "query_table", "{}").name == "query_table"


def test_a_prefixed_submit_answer_is_the_final_answer():
    documents = load_folder(SAMPLE_DIR).documents
    submit = call("submit_answer", {"answer": "Not in the documents.", "kind": "not_found", "sources": []})
    prefixed = LLMReply(content="", tool_calls=[ToolCall(submit.id, "functions.submit_answer", submit.arguments)])
    answer = Agent(FakeLLM([prefixed]), documents).ask("What is the insurance excess?")
    assert answer.answer.startswith("Not in the documents.")
    assert not any("unknown tool" in step for step in answer.steps)
