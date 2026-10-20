"""Tools return exact results, and bad input gives a helpful error, never a crash."""

from pathlib import Path

import pytest

from AI.tools.describe_table import describe_table
from AI.tools.find_dates import find_dates
from AI.tools.list_documents import list_documents
from AI.tools.query_table import query_table
from AI.tools.read_document import read_document
from AI.tools.search_documents import search_documents
from AI.tools.submit_answer import submit_answer
from AI.tools.tool_context import ToolContext, ToolError
from Server.ingestion.folder_loader import load_folder
from tests.sample_content import BOQ_PHASE1_ITEMS, BOQ_PHASE2_AMOUNTS, ELECTRICAL_AMOUNTS

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_docs"
MILLION = 1_000_000


@pytest.fixture(scope="module")
def context():
    return ToolContext(documents=load_folder(SAMPLE_DIR).documents)


def over_million_filter(column: str = "amount") -> list[dict]:
    return [{"column": column, "operator": ">", "value": MILLION}]


def test_list_documents_counts_readable_files(context):
    result = list_documents(context)
    assert result.data["readable"] == 7
    boq = next(d for d in result.data["documents"] if d["name"] == "BOQ_Phase1.xlsx")
    assert {t["table_id"] for t in boq["tables"]} == {"BOQ", "Summary"}


def test_query_table_returns_exactly_the_rows_above_one_million(context):
    result = query_table(context, "BOQ_Phase1.xlsx", "BOQ", over_million_filter())
    table = result.data["tables"][0]
    expected = [item for item in BOQ_PHASE1_ITEMS if item[5] > MILLION]
    assert table["match_count"] == len(expected)
    assert table["sums"]["Total Amount (SAR)"]["sum"] == sum(item[5] for item in expected)
    assert table["rows"][0]["source"] == "BOQ_Phase1.xlsx · BOQ · row 3"
    saved = context.saved_tables[result.data["table_result_id"]]  # every row, for submit_answer
    items = [row[saved["columns"].index("Item")] for row in saved["rows"]]
    assert items == [item[0] for item in expected]
    assert saved["columns"][-1] == "Source"


def test_submit_answer_attaches_saved_rows_exactly(context):
    result = query_table(context, filters=over_million_filter())  # no document: every table
    final = submit_answer(context, "Found **18** items.", table_result_id=result.data["table_result_id"])
    table = final.data["final_answer"].table
    assert len(table["rows"]) == result.data["total_match_count"] == 18
    amounts = [row[table["columns"].index("Amount (SAR)")] for row in table["rows"]]
    assert sum(amounts) == result.data["combined_sum_by_currency"]["SAR"]


def test_submit_answer_removes_markdown_table_when_table_attached(context):
    result = query_table(context, filters=over_million_filter())
    answer = "Found **18** items.\n| Item | Amount |\n|---|---|\n| 3.1 | 6,440,000 |"
    final = submit_answer(context, answer, table_result_id=result.data["table_result_id"])
    assert final.data["final_answer"].answer == "Found **18** items."


def test_submit_answer_with_unknown_table_id_is_a_clear_error(context):
    with pytest.raises(ToolError, match="No saved table"):
        submit_answer(context, "x", table_result_id="t999")


def test_query_table_never_counts_the_total_row(context):
    result = query_table(context, "BOQ_Phase1.xlsx", "BOQ")
    assert result.data["tables"][0]["sums"]["Total Amount (SAR)"]["sum"] == sum(i[5] for i in BOQ_PHASE1_ITEMS)


def test_query_all_documents_skips_summary_sheets_and_keeps_currencies_apart(context):
    result = query_table(context, "*", filters=over_million_filter())
    expected = (
        sum(i[5] for i in BOQ_PHASE1_ITEMS if i[5] > MILLION)
        + sum(a for a in BOQ_PHASE2_AMOUNTS if a and a > MILLION)
        + sum(a for a in ELECTRICAL_AMOUNTS if a > MILLION)
    )
    assert result.data["combined_sum_by_currency"] == {"SAR": expected}
    assert result.data["summary_sheets_left_out"] == ["BOQ_Phase1.xlsx · Summary"]


def test_query_table_sorts_and_limits(context):
    result = query_table(context, "BOQ_Phase1.xlsx", "BOQ", sort_by="amount", limit=2)
    table = result.data["tables"][0]
    assert [row["Item"] for row in table["rows"]] == ["3.1", "2.2"]
    assert table["match_count"] == len(BOQ_PHASE1_ITEMS)


def test_query_pdf_table_cites_the_page(context):
    result = query_table(context, "BOQ_Electrical.pdf", filters=[{"column": "description", "operator": "contains",
                                                                   "value": "cctv"}])  # fmt: skip
    assert result.data["tables"][0]["rows"][0]["source"] == "BOQ_Electrical.pdf · p. 3"


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({"document": "nope.xlsx"}, "No document named"),
        ({"document": "BOQ_Phase1.xlsx"}, "several tables"),
        ({"document": "BOQ_Phase1.xlsx", "table_id": "BOQ", "filters": over_million_filter("zzz")}, "No column"),
        ({"document": "BOQ_Phase1.xlsx", "table_id": "BOQ",
          "filters": [{"column": "amount", "operator": "like", "value": 1}]}, "Unknown operator"),
        ({"document": "BOQ_Phase1.xlsx", "table_id": "BOQ",
          "filters": [{"column": "amount", "operator": ">", "value": "lots"}]}, "not a number"),
        ({"document": "Scanned_Drawing.pdf"}, "cannot be read"),
    ],
)  # fmt: skip
def test_query_table_bad_input_gives_helpful_error(context, arguments, message):
    with pytest.raises(ToolError, match=message):
        query_table(context, **arguments)


def test_describe_table_finds_loose_names(context):
    result = describe_table(context, "boq phase2", "boq phase 2")
    assert result.data["table_id"] == "BOQ Phase 2"
    assert result.data["columns"][-1] == {
        "name": "Amount", "type": "number", "filled": 8, "min": 630000, "max": 2400000, "currency": "SAR",
    }  # fmt: skip


def test_read_document_caps_pages_and_says_what_is_left(context):
    result = read_document(context, "Technical_Specifications.pdf", 1, 50)
    assert len(result.data["pages"]) == 10
    assert "start_page=11" in result.data["more"]


def test_read_document_on_a_spreadsheet_points_to_table_tools(context):
    with pytest.raises(ToolError, match="describe_table"):
        read_document(context, "BOQ_Phase1.xlsx")


def test_find_dates_lists_contract_milestones(context):
    dates = {d["date"]: d["location"] for d in find_dates(context, "Contract_A.pdf").data["dates"]}
    assert dates["31 March 2028"] == "page 3"
    assert dates["Q2 2027"] == "page 3"
    assert "within 28 days" in dates


def test_search_without_vector_store_is_a_clear_error(context):
    with pytest.raises(ToolError, match="not available"):
        search_documents(context, "payment terms")


def test_submit_answer_drops_sources_for_unknown_files_and_pads_rows(context):
    result = submit_answer(
        context,
        "Found **2** items.",
        table={"columns": ["Item", "Amount"], "rows": [["3.1", 6440000], ["2.2"]]},
        sources=[{"document": "boq_phase1", "location": "row 10"}, {"document": "Invented.pdf", "location": "p. 1"}],
    )
    final = result.data["final_answer"]
    assert result.is_final
    assert [s.document for s in final.sources] == ["BOQ_Phase1.xlsx"]
    assert final.table["rows"][1] == ["2.2", None]


def test_submit_answer_combines_several_saved_tables(context):
    ids = [
        query_table(context, name, table, over_million_filter()).data["table_result_id"]
        for name, table in [("BOQ_Phase1.xlsx", "BOQ"), ("BOQ_Electrical.pdf", None)]
    ]
    final = submit_answer(context, "x", table_result_id=",".join(ids)).data["final_answer"]
    expected = sum(i[5] > MILLION for i in BOQ_PHASE1_ITEMS) + sum(a > MILLION for a in ELECTRICAL_AMOUNTS)
    assert len(final.table["rows"]) == expected
    assert final.table["columns"][-1] == "Source"


@pytest.mark.parametrize("document", [None, "*", "None", "null"])
def test_query_all_tables_gives_grand_total_per_currency(context, document):
    result = query_table(context, document)
    expected_sar = sum(i[5] for i in BOQ_PHASE1_ITEMS) + sum(a or 0 for a in BOQ_PHASE2_AMOUNTS)
    expected_sar += sum(ELECTRICAL_AMOUNTS)
    assert result.data["combined_sum_by_currency"] == {"SAR": expected_sar, "USD": 590500}


def test_summary_and_totals_sheets_are_recognised():
    from AI.tools.query_table import SUMMARY_SHEET

    assert all(SUMMARY_SHEET.search(name) for name in ["Summary", "Totals", "Recap", "ملخص"])
    assert not SUMMARY_SHEET.search("BOQ Phase 2")


def test_one_table_query_points_to_other_matching_tables(context):
    result = query_table(context, "BOQ_Electrical.pdf", filters=over_million_filter())
    others = result.data["other_tables_with_these_columns"]
    assert "BOQ_Phase1.xlsx · BOQ" in others and "BOQ_Phase2.xlsx · BOQ Phase 2" in others
    assert "WITHOUT document" in result.data["note"]
    assert "other_tables_with_these_columns" not in query_table(context, filters=over_million_filter()).data
