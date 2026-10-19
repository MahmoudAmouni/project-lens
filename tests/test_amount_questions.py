"""Arabic and Lebanese "items above SAR 1 million" go to query_table, like the English question.

The bug: the Arabic questions were answered with the project scope (an Arabic search hits Arabic_Scope.pdf),
the Lebanese one was labelled "ar", and the Lebanese style example ("14 items") leaked into the answer.
"""

import re
from pathlib import Path

import pytest

from AI.agent import Agent
from AI.question_notes import AMOUNT_NOTE, STYLE_INSTRUCTIONS, asks_for_amount_threshold, question_with_notes
from AI.router import Route, Router
from AI.tools.query_table import query_table
from AI.tools.tool_context import ToolContext, ToolError
from Server.ingestion.folder_loader import load_folder
from tests.fake_llm import FakeLLM, call, tool_reply

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_docs"
MSA_QUESTION = "اذكر جميع البنود التي تزيد قيمتها عن مليون ريال"
LEBANESE_QUESTION = "شو البنود يلي سعرها أكتر من مليون؟"

AMOUNT_QUESTIONS = [
    "List all cost items above SAR 1 million",
    MSA_QUESTION,
    LEBANESE_QUESTION,
    "shu l items yalli aktar men malyon?",
    "items whose value exceeds one million Riyals",
    "List the 2nd floor items over 5m",
]
OTHER_QUESTIONS = [
    "لخص نطاق العمل",
    "قديش قيمة أعمال الواجهات؟",
    "la5asli l scope of work bel contract",
    "What happens if the delay is more than 30 days?",
    "Extract all dates and deliverables",
]


class JsonLLM:
    """The router's model: always returns the same JSON (what the live router returned for the bug)."""

    def __init__(self, reply: dict):
        self.reply = reply

    def complete_json(self, messages):
        return self.reply


@pytest.fixture(scope="module")
def documents():
    return load_folder(SAMPLE_DIR).documents


@pytest.mark.parametrize("question", AMOUNT_QUESTIONS)
def test_amount_threshold_questions_are_found_in_every_style(question):
    assert asks_for_amount_threshold(question)


@pytest.mark.parametrize("question", OTHER_QUESTIONS)
def test_other_questions_get_no_amount_note(question):
    assert not asks_for_amount_threshold(question)


def test_style_examples_hold_no_numbers_the_model_could_copy():
    assert not any(re.search(r"\d", instruction) for instruction in STYLE_INSTRUCTIONS.values())


def test_notes_point_amount_questions_to_query_table_even_without_the_router():
    route = Route(style="ar", intent="document_question")  # the router's fail-safe: no English version
    text = question_with_notes(MSA_QUESTION, route)
    assert AMOUNT_NOTE in text and "search with the English AND the Arabic" not in text


def test_follow_ups_reuse_the_last_answer_instead():
    route = Route(style="ar", intent="follow_up", question_en="Translate the answer")
    assert AMOUNT_NOTE not in question_with_notes(MSA_QUESTION, route)


def test_query_on_every_table_with_an_unknown_sort_column_says_so_instead_of_zero_rows(documents):
    over_a_million = [{"column": "Amount", "operator": ">", "value": 1000000}]
    with pytest.raises(ToolError):
        query_table(ToolContext(documents=documents), filters=over_a_million, sort_by="Price")


def test_lebanese_amount_question_reaches_the_agent_as_ar_lb_with_the_query_table_note(documents):
    router = Router(JsonLLM({"style": "ar", "intent": "document_question",
                             "question_en": "Which items have a price greater than one million?",
                             "question_ar": "أي البنود التي سعرها يزيد عن مليون؟",
                             "search_terms": ["items", "price", "million"]}))  # fmt: skip
    query = call("query_table", {"filters": [{"column": "Amount", "operator": ">", "value": 1000000}]})
    submit = call("submit_answer", {"answer": "في **18** بند.", "table_result_id": "t1",
                                    "sources": [{"document": "BOQ_Phase1.xlsx", "location": "Sheet BOQ"}]})  # fmt: skip
    llm = FakeLLM([tool_reply(query), tool_reply(submit)])
    answer = Agent(llm, documents, router=router).ask(LEBANESE_QUESTION, ui_language="ar")
    question_sent = llm.requests[0]["messages"][-1]["content"]
    assert answer.style == "ar-lb" and "Lebanese Arabic" in question_sent
    assert AMOUNT_NOTE in question_sent
    assert answer.steps == [
        "Filtered BOQ_Electrical.pdf · page_2_table_1, BOQ_Phase1.xlsx · BOQ, BOQ_Phase2.xlsx · BOQ Phase 2: 18 rows"
    ]
