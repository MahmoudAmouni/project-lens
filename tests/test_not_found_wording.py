"""An answer that SAYS nothing was found also names the unreadable files, even when the model sent kind "answer"."""

from pathlib import Path

import pytest

from AI.agent import Agent
from AI.language.not_found_words import opens_with_not_found, says_not_found
from Server.ingestion.folder_loader import load_folder
from tests.fake_llm import FakeLLM, call, tool_reply

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_docs"


@pytest.fixture(scope="module")
def documents():
    return load_folder(SAMPLE_DIR).documents


@pytest.mark.parametrize(
    "text",
    ["I could not find the insurance excess in the documents.", "I couldn't locate that amount.",
     "I cannot determine the milestone 3 amount.", "There is no information about the insurance excess.",
     "The excess is not mentioned in the contract.", "The value was not found in the BOQ.",
     "لم أجد هذه المعلومة في المستندات.", "ما لقيت هالمعلومة بالملفات.", "Ma la2et hal ma3lume bel files."],
)  # fmt: skip
def test_not_found_wording_in_every_style(text):
    assert says_not_found(text)


@pytest.mark.parametrize(
    "text",
    ["The contract sum is SAR 48,750,000.", "Retention is **5%**, found on page 4.", "المبلغ هو 5,000 ريال.",
     "The notice must be given within 14 days.", ""],
)  # fmt: skip
def test_normal_answers_are_left_alone(text):
    assert not says_not_found(text)


def test_an_answer_kind_that_says_not_found_gets_the_note(documents):
    read = tool_reply(call("read_document", {"document": "Contract_A.pdf", "start_page": 4, "end_page": 4}))
    text = "I could not find the insurance excess in the contract."
    submit = tool_reply(call("submit_answer", {"answer": text, "sources": [{"document": "Contract_A.pdf", "page": 4}]}))
    answer = Agent(FakeLLM([read, submit]), documents).ask("What is the insurance excess?")
    assert answer.answer.startswith(text)
    assert "These files could not be read" in answer.answer
    assert all(document.name in answer.answer for document in documents if document.status != "ok")


def test_a_found_answer_gets_no_note(documents):
    read = tool_reply(call("read_document", {"document": "Contract_A.pdf", "start_page": 4, "end_page": 4}))
    text = "Retention is **5%**."
    submit = tool_reply(call("submit_answer", {"answer": text, "sources": [{"document": "Contract_A.pdf", "page": 4}]}))
    assert Agent(FakeLLM([read, submit]), documents).ask("What is the retention?").answer == text


def test_a_whole_not_found_answer_shows_no_searched_file_as_a_source(documents):
    read = tool_reply(call("read_document", {"document": "Contract_A.pdf", "start_page": 4, "end_page": 4}))
    text = "I could not find the insurance excess. I searched the contract and the specifications."
    submit = tool_reply(call("submit_answer", {"answer": text, "sources": [{"document": "Contract_A.pdf", "page": 4}]}))
    answer = Agent(FakeLLM([read, submit]), documents).ask("What is the insurance excess?")
    assert (answer.kind, answer.sources) == ("not_found", [])


@pytest.mark.parametrize(
    ("text", "question", "whole"),
    [("I could not find the excess.", "", True), ("I could not find milestone 3.", "milestone 3?", True),
     ("Retention is 5%. The excess is not mentioned.", "", False),
     ("I could not find the excess, but the cover is 110%.", "", False), ("The sum is SAR 5,000.", "", False)],
)  # fmt: skip
def test_only_a_whole_not_found_answer_loses_its_sources(text, question, whole):
    assert opens_with_not_found(text, question) is whole
