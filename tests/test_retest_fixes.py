"""Bugs found by the second live hard test: shorthand amounts, text in number columns, Arabic "not found" wording."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from AI.agent import Agent
from AI.guards.number_check import keep_tool_numbers, known_numbers, unsupported_numbers
from AI.language.not_found_words import opens_with_not_found, says_not_found
from AI.language.replies import EXAMPLES
from AI.tools.query_table import BIG_ROWS_FOR_MODEL, ROWS_FOR_MODEL, query_table
from AI.tools.search_documents import search_documents
from AI.tools.tool_context import ToolContext
from Server.ingestion.folder_loader import load_folder
from Server.ingestion.table_cleaner import CELL_NOTE, clean_table
from tests.fake_llm import FakeLLM, call, text_reply, tool_reply


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


def ask_after_query(answer_text: str):
    documents = load_folder(Path(__file__).resolve().parent.parent / "sample_docs").documents
    query = tool_reply(call("query_table", {"document": "BOQ_Phase1.xlsx", "table_id": "BOQ"}))
    source = {"document": "BOQ_Phase1.xlsx", "location": "Sheet BOQ"}
    submit = tool_reply(call("submit_answer", {"answer": answer_text, "sources": [source]}))
    return Agent(FakeLLM([query, submit]), documents).ask("List every item in the BOQ")


def test_query_rows_are_attached_when_the_answer_quotes_them():
    answer = ask_after_query("Site clearance is SAR 180,000 and excavation SAR 1,176,000.")
    assert answer.table and len(answer.table["rows"]) > 8 and "Source" in answer.table["columns"]


def test_rows_from_a_side_search_are_not_attached():
    assert ask_after_query("The advance payment is 15% of the contract sum.").table is None


def test_one_file_search_reports_other_files_with_the_words():
    passages = [
        {"document": "Agreement.pdf", "location": "page 4", "text": "Advance payment of 15%.", "score": 0.9},
        {"document": "ملحق_العقد.pdf", "location": "page 1", "text": "عدد المصاعد المطلوبة: 9 مصاعد", "score": 0.5},
        {"document": "BOQ.xlsx", "location": "row 3", "text": "Excavation to reduced levels", "score": 0.4},
    ]
    store = SimpleNamespace(search=lambda query, document=None, top_k=6: [
        p for p in passages if document in (None, p["document"])
    ])  # fmt: skip
    documents = [SimpleNamespace(name=n, status="ok") for n in ("Agreement.pdf", "ملحق_العقد.pdf", "BOQ.xlsx")]
    result = search_documents(ToolContext(documents=documents, vector_store=store), "المصاعد", "Agreement.pdf")
    assert [f["document"] for f in result.data["also_in_other_files"]] == ["ملحق_العقد.pdf"]
    assert "also found in 1 other file" in result.step


def test_percentage_columns_are_never_added_up():
    rows = [["Zone", "Planned %", "Actual %", "Amount (SAR)"], ["North", 12, 7.5, 1000], ["South", 9, 8.2, 2000],
            ["Central", 8.5, 5.6, 3000]]  # fmt: skip
    table = SimpleNamespace(id="Zones", data=clean_table(rows).data, location="page 1", currencies={},
                            summary_rows=[], notes=[])  # fmt: skip
    document = SimpleNamespace(name="Weekly.docx", status="ok", tables=[table], pages=[], file_type="word")
    result = query_table(ToolContext(documents=[document]), "Weekly.docx", "Zones").data["tables"][0]
    assert "Planned %" not in result["sums"] and "Actual %" not in result["sums"]
    assert result["sums"]["Amount (SAR)"]["sum"] == 6000
    assert "never added up" in result["not_added"]


def test_plain_text_replies_lose_their_history_tags():
    documents = load_folder(Path(__file__).resolve().parent.parent / "sample_docs").documents
    read = tool_reply(call("read_document", {"document": "Contract_A.pdf", "start_page": 4, "end_page": 4}))
    text = "Retention is **5%**.\n\n[Sources: Contract_A.pdf — page 4]"
    llm = FakeLLM([read, text_reply(text), text_reply(text)])
    answer = Agent(llm, documents).ask("What is the retention?")
    assert "[Sources:" not in answer.answer and answer.answer.startswith("Retention is **5%**.")


def test_suggestions_name_no_currency():
    assert not any("SAR" in q or "ريال" in q for questions in EXAMPLES.values() for _, q in questions)
