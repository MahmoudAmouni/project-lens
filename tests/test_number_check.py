"""Numbers in an answer must come from the tools; made-up ones are removed before the user sees them."""

from pathlib import Path

import pytest

from AI.agent import Agent
from AI.guards.number_check import known_numbers, unsupported_numbers
from Server.ingestion.folder_loader import load_folder
from tests.fake_llm import FakeLLM, call, text_reply, tool_reply

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_docs"
UNIT_RATE_QUERY = call(
    "query_table",
    {"document": "BOQ_Phase1.xlsx", "table_id": "BOQ",
     "filters": [{"column": "Unit Rate (SAR)", "operator": ">", "value": 500}]},
)  # fmt: skip
MADE_UP_ANSWER = (
    "There are 7 items with a unit rate above 500 SAR:\n"
    "* Supply and install precast concrete boundary wall with a unit rate of 550 SAR\n"
    "* Supply and install CCTV cameras with a unit rate of 700 SAR"
)


@pytest.fixture(scope="module")
def documents():
    return load_folder(SAMPLE_DIR).documents


def test_made_up_numbers_are_found():
    known = known_numbers(["Unit Rate 780, 920, 690; Total 1176000", "unit rate above 500"])
    assert unsupported_numbers(MADE_UP_ANSWER, known) == [550.0, 700.0]


def test_real_rounded_scaled_and_arabic_numbers_pass():
    known = known_numbers(["Total 1176000, 21186000, Qty 1200, Rate 865000"])
    text = "SAR 21.2 million in total, about 1.2M for excavation, 1200 m of wall, ٨٦٥٬٠٠٠ ريال, item 2.2.1, C40"
    assert unsupported_numbers(text, known) == []


def test_plain_numbers_must_match_exactly():
    assert unsupported_numbers("about 1,200,000", known_numbers(["1176000"])) == [1200000.0]


def test_made_up_rows_are_replaced_by_the_real_saved_rows(documents):
    llm = FakeLLM([tool_reply(UNIT_RATE_QUERY), tool_reply(call("submit_answer", {"answer": MADE_UP_ANSWER}))])
    answer = Agent(llm, documents).ask("what is the description of unit rate above 500")
    assert answer.kind == "answer" and "550" not in answer.answer and "700" not in answer.answer
    assert answer.answer == "There are 7 items with a unit rate above 500 SAR:"  # the true sentence stays
    descriptions = [row[answer.table["columns"].index("Description")] for row in answer.table["rows"]]
    assert len(descriptions) == 7 and "Structural steel frame" in descriptions
    assert "Removed a sentence with a number the tools did not return" in answer.steps


def test_made_up_numbers_without_any_rows_become_not_found(documents):
    llm = FakeLLM([text_reply(MADE_UP_ANSWER), text_reply(MADE_UP_ANSWER)])
    answer = Agent(llm, documents).ask("what is the description of unit rate above 500")
    assert answer.kind == "not_found" and "550" not in answer.answer


def test_answer_with_tool_numbers_is_kept(documents):
    real = "Structural steel frame has the highest unit rate: 5,600 SAR per tonne."
    llm = FakeLLM([tool_reply(UNIT_RATE_QUERY), tool_reply(call("submit_answer", {"answer": real}))])
    answer = Agent(llm, documents).ask("which item has the highest unit rate above 500?")
    assert answer.answer == real
