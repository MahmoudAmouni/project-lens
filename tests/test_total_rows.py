"""Subtotal and grand total lines asked for with include_total_rows are marked, so the screen never adds them up."""

from pathlib import Path

import pytest

from AI.tools.query_table import query_table
from AI.tools.saved_tables import combine_saved_tables
from AI.tools.tool_context import ToolContext
from Server.ingestion.folder_loader import load_folder
from Server.schemas.chat_schemas import TableData

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_docs"


@pytest.fixture()
def context():
    return ToolContext(documents=load_folder(SAMPLE_DIR).documents)


def boq_table(context):
    document = next(d for d in context.documents if d.name == "BOQ_Phase1.xlsx")
    return next(t for t in document.tables if t.id == "BOQ")


def test_total_lines_are_marked_when_asked_for(context):
    table = boq_table(context)
    assert table.summary_rows  # the sample BOQ has subtotal / total lines
    result = query_table(context, "BOQ_Phase1.xlsx", "BOQ", include_total_rows=True, sort_by="amount")  # total first
    marked = [row["row"] for row in result.data["tables"][0]["rows"] if row.get("is_total")]
    assert marked and set(marked) <= set(table.summary_rows)


def test_normal_rows_are_not_marked(context):
    result = query_table(context, "BOQ_Phase1.xlsx", "BOQ")
    assert not any(row.get("is_total") for row in result.data["tables"][0]["rows"])


def test_the_saved_table_lists_its_total_lines_and_they_survive_combining(context):
    first = query_table(context, "BOQ_Phase1.xlsx", "BOQ", include_total_rows=True).data["table_result_id"]
    second = query_table(context, "BOQ_Phase1.xlsx", "BOQ", include_total_rows=True, limit=3).data["table_result_id"]
    one = combine_saved_tables(context, [first])
    both = combine_saved_tables(context, [second, first])
    assert one["total_rows"]
    shift = len(context.saved_tables[second]["rows"])
    assert both["total_rows"][-len(one["total_rows"]) :] == [index + shift for index in one["total_rows"]]
    assert "__is_total" not in one["columns"] and "is_total" not in one["columns"]


def test_a_table_without_total_lines_has_no_total_rows_key(context):
    saved_id = query_table(context, "BOQ_Phase1.xlsx", "BOQ").data["table_result_id"]
    assert "total_rows" not in combine_saved_tables(context, [saved_id])


def test_the_api_table_accepts_total_rows():
    assert TableData(columns=["Item"], rows=[["A"], ["Total"]], total_rows=[1]).total_rows == [1]
    assert TableData(columns=["Item"], rows=[["A"]]).total_rows == []


def test_sums_never_add_the_total_lines(context):
    plain = query_table(context, "BOQ_Phase1.xlsx", "BOQ").data["tables"][0]
    with_totals = query_table(context, "BOQ_Phase1.xlsx", "BOQ", include_total_rows=True).data["tables"][0]
    assert with_totals["sums"] == plain["sums"]  # asking to see the total lines must not double the sums
    assert with_totals["match_count"] > plain["match_count"]
