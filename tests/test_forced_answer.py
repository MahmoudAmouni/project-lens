"""When the round limit is hit, the last request still carries what the FIRST rounds found."""

from pathlib import Path

import pytest

from AI.agent import MAX_TOOL_ROUNDS, Agent
from AI.findings import MAX_LINES, findings_digest
from AI.messages import summary_messages
from AI.prompts import FINDINGS_HEADER
from Server.ingestion.folder_loader import load_folder
from tests.fake_llm import FakeLLM, call, tool_reply

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_docs"
FOUND = '{"pages": [{"page": 4, "text": "3.2 Retention of 5% shall be deducted from each interim payment."}]}'
EMPTY = '{"passages": [{"text": "Clause 9 covers site access and working hours."}]}'


@pytest.fixture(scope="module")
def documents():
    return load_folder(SAMPLE_DIR).documents


def test_the_digest_keeps_an_early_finding_and_skips_unrelated_lines():
    digest = findings_digest("The contract says retention is 20%, right?\n\n[Notes for you]\n- Reply in English", [
        FOUND, EMPTY, EMPTY,
    ])  # fmt: skip
    assert digest == "- 3.2 Retention of 5% shall be deducted from each interim payment."


def test_the_digest_is_empty_without_matches_and_capped_in_length():
    assert findings_digest("What is the retention?", [EMPTY]) == ""
    many = [f'{{"text": "Retention line number {number} of the contract."}}' for number in range(30)]
    assert len(findings_digest("retention", many).splitlines()) == MAX_LINES


def test_the_short_summary_uses_the_real_question_not_a_reminder():
    messages = [{"role": "system", "content": "rules"}, {"role": "user", "content": "Reminder: answer now"}]
    summary = summary_messages("What is the retention?", messages, ["Searched"], "- Retention of 5%")
    assert summary[1]["content"].startswith("What is the retention?")
    assert FINDINGS_HEADER in summary[1]["content"] and "- Retention of 5%" in summary[1]["content"]


def test_the_forced_last_request_shows_the_round_one_finding(documents):
    read = tool_reply(call("read_document", {"document": "Contract_A.pdf", "start_page": 4, "end_page": 4}))
    searches = [
        tool_reply(call("search_documents", {"query": f"retention clause {number}"}, call_id=f"s{number}"))
        for number in range(MAX_TOOL_ROUNDS)
    ]
    final = tool_reply(call("submit_answer", {"answer": "Not found.", "kind": "not_found", "sources": []}))
    llm = FakeLLM([read, *searches, final])
    Agent(llm, documents).ask("What is the retention?")
    last_request = llm.requests[-1]["messages"][-1]["content"]
    assert FINDINGS_HEADER in last_request
    assert "Retention" in last_request.split(FINDINGS_HEADER, 1)[1]
