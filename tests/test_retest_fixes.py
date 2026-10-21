"""Bugs found by the second live hard test: shorthand amounts, text in number columns, Arabic "not found" wording."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from AI.agent import Agent
from AI.guards.number_check import keep_tool_numbers, known_numbers, unsupported_numbers
from AI.language.not_found_words import opens_with_not_found, says_not_found
from AI.tools.query_table import BIG_ROWS_FOR_MODEL, ROWS_FOR_MODEL, query_table
from AI.tools.tool_context import ToolContext
from Server.ingestion.folder_loader import load_folder
from Server.ingestion.table_cleaner import CELL_NOTE, clean_table
from tests.fake_llm import FakeLLM, call, tool_reply


@pytest.mark.parametrize(
    ("question", "value"),
    [("wich items r more then 5mil", 5e6), ("above 5 mill", 5e6), ("over 1.5 mn", 1.5e6), ("2 malayin", 2e6),
     ("أكثر من ٥ ملايين", 5e6), ("aktar men malyon", 1e6), ("above a million", 1e6), ("2,000 thousands", 2e6)],
)  # fmt: skip
def test_shorthand_amounts_in_the_question_are_known(question, value):
    assert value in known_numbers([question])


def test_restating_the_user_threshold_is_allowed_but_new_numbers_are_not():
    known = known_numbers(["wich items r more then 5mil"])
    assert unsupported_numbers("Items above 5,000,000 SAR:", known) == []
    assert unsupported_numbers("Items above 7,000,000 SAR:", known) == [7e6]


def test_metres_and_codes_are_not_millions():
    assert known_numbers(["150 m long", "grade C40"]) == {150.0}


def test_text_in_a_number_column_is_kept_as_a_cell_note():
    rows = [
        ["Ref", "Description", "Rate (SAR)", "Amount (SAR)"],
        ["C3", "Rooflights", 215, 408500],
        ["C4", "Crane rail supports", "RO", "Rate Only"],
        ["C5", "Gutters", 120, 60000],
        ["C6", "Downpipes", 80, 40000],
        ["C7", "Flashings", 60, 30000],
    ]
    cleaned = clean_table(rows)
    data = cleaned.data
    assert data.loc[data["Ref"] == "C4", CELL_NOTE].item() == "Rate (SAR): RO; Amount (SAR): Rate Only"
    assert data["Amount (SAR)"].sum() == 538500  # the note never changes the numbers
    assert data[CELL_NOTE].notna().sum() == 1


def test_a_table_without_text_in_number_columns_has_no_note_column():
    cleaned = clean_table([["Ref", "Amount (SAR)"], ["A1", 100], ["A2", 200]])
    assert CELL_NOTE not in cleaned.data.columns


@pytest.mark.parametrize(
    "text",
    ["المستندات اللي معنا ما فيها أي معلومات عن أسعار السوق.", "لا تحتوي المستندات على أسعار السوق.",
     "The documents do not contain market prices.", "The files contain no steel prices.",
     "ma fiha ay ma3lume 3an l as3ar"],
)  # fmt: skip
def test_more_not_found_wording_is_a_whole_not_found(text):
    assert says_not_found(text) and opens_with_not_found(text)


@pytest.mark.parametrize("text", ["The contract contains 12 clauses.", "ما في بند أكتر من مليون", "Retention is 5%."])
def test_real_answers_are_not_not_found(text):
    assert not opens_with_not_found(text)


def test_big_limit_models_see_more_rows_than_groq():
    context = ToolContext(documents=load_folder(Path(__file__).resolve().parent.parent / "sample_docs").documents)
    small = query_table(context, "BOQ_Phase1.xlsx", "BOQ").data["tables"][0]
    context.rows_for_model = BIG_ROWS_FOR_MODEL
    big = query_table(context, "BOQ_Phase1.xlsx", "BOQ").data["tables"][0]
    assert len(small["rows"]) == ROWS_FOR_MODEL < len(big["rows"]) == big["match_count"]
    assert "rows_not_shown_here" in small and "rows_not_shown_here" not in big


def test_the_model_table_is_kept_when_only_its_text_had_made_up_numbers():
    real = {"columns": ["Item", "Amount", "Source"], "rows": [["A1", 156000, "BOQ.xlsx · BOQ · row 7"]]}
    saved = {"t1": {"columns": ["Section", "Amount", "Source"], "rows": [["A", 2900425, "BOQ.xlsx · Summary · row 2"]]}}
    answer = SimpleNamespace(kind="answer", answer="A1 is 156,000 and A9 is 7,500.", table=real, sources=[], steps=[])
    kept = keep_tool_numbers(answer, ["A1 156000"], SimpleNamespace(saved_tables=saved), ["t1"], "en")
    assert kept.table is real and "7,500" not in kept.answer


def test_a_model_table_with_made_up_numbers_is_replaced():
    fake = {"columns": ["Item", "Amount", "Source"], "rows": [["A9", 7500, "BOQ.xlsx · BOQ · row 9"]]}
    saved = {"t1": {"columns": ["Section", "Amount", "Source"], "rows": [["A", 2900425, "BOQ.xlsx · Summary · row 2"]]}}
    answer = SimpleNamespace(kind="answer", answer="A9 is 7,500.", table=fake, sources=[], steps=[])
    kept = keep_tool_numbers(answer, ["A 2900425"], SimpleNamespace(saved_tables=saved), ["t1"], "en")
    assert kept.table["rows"] == [["A", 2900425, "BOQ.xlsx · Summary · row 2"]]


def test_query_rows_are_attached_when_the_model_forgets_the_table():
    documents = load_folder(Path(__file__).resolve().parent.parent / "sample_docs").documents
    query = tool_reply(call("query_table", {"document": "BOQ_Phase1.xlsx", "table_id": "BOQ"}))
    source = {"document": "BOQ_Phase1.xlsx", "location": "Sheet BOQ"}
    submit = tool_reply(call("submit_answer", {"answer": "Here are the BOQ items.", "sources": [source]}))
    answer = Agent(FakeLLM([query, submit]), documents).ask("List every item in the BOQ")
    assert answer.table and len(answer.table["rows"]) > 8 and "Source" in answer.table["columns"]
