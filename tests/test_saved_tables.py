"""Saved query_table rows belong to one question: a later answer can never attach an older table."""

from pathlib import Path

import pytest

from AI.agent import Agent
from Server.ingestion.folder_loader import load_folder
from tests.fake_llm import FakeLLM, call, tool_reply

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_docs"
SOURCE = [{"document": "BOQ_Phase1.xlsx", "location": "Sheet BOQ"}]
OVER_A_MILLION = [{"column": "amount", "operator": ">", "value": 1000000}]
QUERY = call("query_table", {"document": "BOQ_Phase1.xlsx", "table_id": "BOQ", "filters": OVER_A_MILLION})


def submit(table_id: str | None = None) -> object:
    arguments = {"answer": "Here are the items.", "sources": SOURCE}
    if table_id:
        arguments["table_result_id"] = table_id
    return tool_reply(call("submit_answer", arguments, call_id=f"submit_{table_id}"))


@pytest.fixture(scope="module")
def documents():
    return load_folder(SAMPLE_DIR).documents


def test_a_table_saved_in_this_question_is_attached(documents):
    answer = Agent(FakeLLM([tool_reply(QUERY), submit("t1")]), documents).ask("Items above SAR 1 million?")
    assert answer.table is not None and len(answer.table["rows"]) == 9


def test_a_table_from_an_earlier_question_cannot_be_attached(documents):
    llm = FakeLLM([tool_reply(QUERY), submit("t1"), submit("t1"), submit()])
    agent = Agent(llm, documents)
    first = agent.ask("Items above SAR 1 million?")
    second = agent.ask("And the contract dates?")  # the model tries to reuse t1 without querying again
    assert first.table is not None
    assert second.table is None
    tool_message = llm.requests[3]["messages"][-1]
    assert tool_message["role"] == "tool" and "No saved table 't1'. Saved tables: none" in tool_message["content"]


def test_table_numbers_start_again_for_each_question(documents):
    llm = FakeLLM([tool_reply(QUERY), submit("t1"), tool_reply(QUERY), submit("t1")])
    agent = Agent(llm, documents)
    agent.ask("Items above SAR 1 million?")
    second = agent.ask("Same list again please")
    assert second.table is not None and list(agent.context.saved_tables) == ["t1"]
