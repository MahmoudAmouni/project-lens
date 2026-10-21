"""Numbers from earlier answers count as known only for a follow-up on them; a new question needs the tools again."""

from pathlib import Path

import pytest

from AI.agent import Agent
from AI.language.follow_up_words import looks_like_follow_up
from AI.router import Router, fallback_route
from Server.ingestion.folder_loader import load_folder
from tests.fake_llm import FakeLLM, call, tool_reply

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_docs"
OLD_ANSWER = {"role": "assistant", "content": "The total is **SAR 999,999**.\n\n[Sources: Contract_A.pdf — page 4]"}
HISTORY = [{"role": "user", "content": "What is the total?"}, OLD_ANSWER]


@pytest.fixture(scope="module")
def documents():
    return load_folder(SAMPLE_DIR).documents


@pytest.mark.parametrize(
    "text",
    ["write that in Arabic", "translate the answer", "and the second one?", "shorten it", "ترجم الجواب للإنجليزي",
     "اكتب هيدا بالعربي", "w l tene?", "tarjemle ya bel english"],
)  # fmt: skip
def test_follow_up_messages(text):
    assert looks_like_follow_up(text)


@pytest.mark.parametrize(
    "text",
    ["What is the retention percentage?", "List all items above SAR 1 million", "شو أكبر ٣ بنود بالـ MEP؟",
     "shu l items bel civil BOQ yalli aktar men malyon?"],
)  # fmt: skip
def test_new_questions_are_not_follow_ups(text):
    assert not looks_like_follow_up(text)


def test_the_fail_safe_needs_chat_history_to_call_it_a_follow_up():
    assert fallback_route("write that in Arabic", "en", HISTORY).intent == "follow_up"
    assert fallback_route("write that in Arabic", "en", []).intent == "document_question"


def reused_old_number() -> list:
    """The model reads a page, then answers with the number from the OLD answer instead of a tool result."""
    read = tool_reply(call("read_document", {"document": "Contract_A.pdf", "start_page": 4, "end_page": 4}))
    source = {"document": "Contract_A.pdf", "page": 4}
    submit = tool_reply(call("submit_answer", {"answer": "The total is **SAR 999,999**.", "sources": [source]}))
    return [read, submit]


def test_a_new_question_cannot_reuse_a_number_from_an_old_answer(documents):
    answer = Agent(FakeLLM(reused_old_number()), documents, router=Router()).ask("What is the retention?", HISTORY)
    assert "999,999" not in answer.answer


def test_a_follow_up_may_reuse_the_numbers_of_the_answer_it_is_about(documents):
    answer = Agent(FakeLLM(reused_old_number()), documents, router=Router()).ask("write that in Arabic", HISTORY)
    assert "999,999" in answer.answer
