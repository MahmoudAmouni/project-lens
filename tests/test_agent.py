"""The agent loop, tested with a fake LLM: tool rounds, guards, the round limit and the final answer."""

from pathlib import Path

import pytest

from AI.agent import MAX_TOOL_ROUNDS, Agent
from Server.ingestion.folder_loader import load_folder
from tests.fake_llm import FakeLLM, broken_call_error, call, text_reply, tool_reply

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_docs"

SUBMIT = call(
    "submit_answer",
    {"answer": "Found **9 items**.", "sources": [{"document": "BOQ_Phase1.xlsx", "location": "Sheet BOQ"}]},
)


@pytest.fixture(scope="module")
def documents():
    return load_folder(SAMPLE_DIR).documents


def test_tools_run_then_submit_answer_ends_the_loop(documents):
    llm = FakeLLM([
        tool_reply(call("list_documents")),
        tool_reply(call("query_table", {"document": "BOQ_Phase1.xlsx", "table_id": "BOQ",
                                        "filters": [{"column": "amount", "operator": ">", "value": 1000000}]})),
        tool_reply(SUBMIT),
    ])  # fmt: skip
    answer = Agent(llm, documents).ask("List cost items above SAR 1 million")
    assert answer.answer == "Found **9 items**."
    assert answer.sources == [{"document": "BOQ_Phase1.xlsx", "location": "Sheet BOQ", "snippet": ""}]
    assert answer.steps == ["Listed 11 documents (6 readable)", "Filtered BOQ_Phase1.xlsx · BOQ: 9 rows"]
    tool_message = llm.requests[2]["messages"][-1]
    assert tool_message["role"] == "tool" and tool_message["tool_call_id"] == "call_query_table"
    assert '"match_count": 9' in tool_message["content"]


def test_broken_json_arguments_are_sent_back_to_the_model(documents):
    llm = FakeLLM([tool_reply(call("query_table", "{not json")), tool_reply(SUBMIT)])
    Agent(llm, documents).ask("question")
    assert "not valid JSON" in llm.requests[1]["messages"][-1]["content"]


def test_groq_tool_use_failed_error_asks_the_model_to_retry(documents):
    llm = FakeLLM([broken_call_error(), tool_reply(SUBMIT)])
    answer = Agent(llm, documents).ask("question")
    assert answer.answer == "Found **9 items**."
    assert "not valid JSON" in llm.requests[1]["messages"][-1]["content"]


def test_unknown_tool_name_lists_the_real_tools(documents):
    llm = FakeLLM([tool_reply(call("delete_everything")), tool_reply(SUBMIT)])
    Agent(llm, documents).ask("question")
    assert "Tools: list_documents" in llm.requests[1]["messages"][-1]["content"]


def test_plain_text_reply_gets_one_reminder_then_is_used(documents):
    llm = FakeLLM([text_reply("I can only answer from the loaded documents.")])
    answer = Agent(llm, documents).ask("hi")
    assert answer.answer == "I can only answer from the loaded documents."
    assert answer.sources == []
    assert len(llm.requests) == 2
    assert "call submit_answer" in llm.requests[1]["messages"][-1]["content"]


def test_plain_text_then_submit_gives_structured_answer(documents):
    llm = FakeLLM([text_reply("Here are the items: ..."), tool_reply(SUBMIT)])
    answer = Agent(llm, documents).ask("question")
    assert answer.answer == "Found **9 items**."


def test_old_tool_results_are_shortened(documents):
    llm = FakeLLM([
        tool_reply(call("read_document", {"document": "Technical_Specifications.pdf"}, call_id="r1")),
        tool_reply(call("list_documents", call_id="l1")),
        tool_reply(SUBMIT),
    ])  # fmt: skip
    Agent(llm, documents).ask("question")
    old_result = next(m for m in llm.requests[2]["messages"] if m.get("tool_call_id") == "r1")
    assert old_result["content"].endswith('"[shortened]"')


def test_round_limit_forces_a_final_answer(documents):
    script = [tool_reply(call("list_documents", call_id=f"c{i}")) for i in range(MAX_TOOL_ROUNDS)]
    llm = FakeLLM([*script, tool_reply(SUBMIT)])
    answer = Agent(llm, documents).ask("question")
    assert answer.answer == "Found **9 items**."
    assert answer.steps[-1] == f"Stopped after {MAX_TOOL_ROUNDS} rounds"
    last_request = llm.requests[-1]
    assert last_request["tool_choice"]["function"]["name"] == "submit_answer"
    assert [t["function"]["name"] for t in last_request["tools"]] == ["submit_answer"]


def test_history_is_limited_to_the_last_six_messages(documents):
    history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"} for i in range(10)]
    llm = FakeLLM([tool_reply(SUBMIT)])
    Agent(llm, documents).ask("new question", history)
    sent = llm.requests[0]["messages"]
    assert [m["content"] for m in sent[1:-1]] == ["m4", "m5", "m6", "m7", "m8", "m9"]
    assert sent[-1] == {"role": "user", "content": "new question"}


def test_exact_repeated_tool_call_is_refused(documents):
    read = {"document": "Contract_A.pdf", "start_page": 2, "end_page": 2}
    llm = FakeLLM([
        tool_reply(call("read_document", read, call_id="a")),
        tool_reply(call("read_document", read, call_id="b")),
        tool_reply(SUBMIT),
    ])  # fmt: skip
    answer = Agent(llm, documents).ask("question")
    assert "already made this exact call" in llm.requests[2]["messages"][-1]["content"]
    assert answer.steps[0] == "Read Contract_A.pdf page 2"


def test_failed_forced_answer_falls_back_to_a_tiny_request(documents):
    rounds = [tool_reply(call("find_dates", {"document": f"Contract_A.pdf{'.' * i}"}, call_id=f"c{i}"))
              for i in range(MAX_TOOL_ROUNDS)]  # fmt: skip
    llm = FakeLLM([*rounds, broken_call_error(), tool_reply(SUBMIT)])
    answer = Agent(llm, documents).ask("question")
    assert answer.answer == "Found **9 items**."
    assert len(llm.requests[-1]["messages"]) == 2  # system + one short summary message


def test_model_is_told_to_answer_after_many_searches(documents):
    store = type("Store", (), {"search": lambda self, query, document=None, top_k=6: []})()
    searches = [tool_reply(call("search_documents", {"query": f"q{i}"}, call_id=f"s{i}")) for i in range(4)]
    llm = FakeLLM([*searches, tool_reply(SUBMIT)])
    Agent(llm, documents, vector_store=store).ask("question")
    assert "already searched 4 times" in llm.requests[4]["messages"][-1]["content"]


def test_loaded_files_are_listed_in_the_system_prompt(documents):
    llm = FakeLLM([tool_reply(SUBMIT)])
    Agent(llm, documents).ask("question")
    system = llm.requests[0]["messages"][0]["content"]
    assert "table 'BOQ' (18 rows: Item, Description" in system
    assert "Scanned_Drawing.pdf: cannot be read (scanned)" in system
