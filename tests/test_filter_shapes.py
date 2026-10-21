"""query_table reads filters in the shapes other models write them: JSON text, {column: value}, "op" (no API calls)."""

from pathlib import Path

import pytest

from AI.tools.filter_shapes import normal_columns, normal_filters, normal_flag
from AI.tools.query_table import query_table
from AI.tools.tool_context import ToolContext, ToolError
from Server.ingestion.folder_loader import load_folder
from tests.sample_content import BOQ_PHASE1_ITEMS

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_docs"
MILLION = 1_000_000
OVER_MILLION = [{"column": "amount", "operator": ">", "value": MILLION}]


@pytest.fixture(scope="module")
def context():
    return ToolContext(documents=load_folder(SAMPLE_DIR).documents)


@pytest.mark.parametrize(
    "filters",
    ['[{"column": "amount", "operator": ">", "value": 1000000}]', {"amount": {">": MILLION}},
     [{"field": "amount", "op": ">", "value": MILLION}], ['{"column": "amount", "operator": ">", "value": 1000000}'],
     {"column": "amount", "operator": ">", "value": MILLION}],
)  # fmt: skip
def test_every_shape_gives_the_same_filter(filters):
    assert normal_filters(filters) == OVER_MILLION


def test_a_plain_column_value_pair_means_equals():
    assert normal_filters({"Milestone": 3}) == [{"column": "Milestone", "operator": "=", "value": 3}]
    assert normal_filters('{"Milestone": 3}') == [{"column": "Milestone", "operator": "=", "value": 3}]


def test_no_filters_in_any_shape():
    assert normal_filters(None) == normal_filters("") == normal_filters("[]") == normal_filters({}) == []


def test_unreadable_filters_explain_the_right_shape():
    with pytest.raises(ToolError, match="Write filters as"):
        normal_filters("[{column: amount")
    with pytest.raises(ToolError, match="Write filters as"):
        normal_filters(["amount > 1000000"])


def test_columns_as_text_become_a_list():
    assert normal_columns('["Item", "Total Amount (SAR)"]') == ["Item", "Total Amount (SAR)"]
    assert normal_columns("Item, Description") == ["Item", "Description"]
    assert normal_columns(None) is None


def test_flags_written_as_text():
    assert normal_flag("false", True) is False and normal_flag("true", False) is True and normal_flag(None, True)


def test_query_table_with_json_text_filters_and_columns(context):
    """The exact shapes a free OpenRouter model sent in the live test."""
    result = query_table(
        context, "BOQ_Phase1.xlsx", "BOQ", '[{"column": "amount", "operator": ">", "value": 1000000}]',
        columns='["Item", "Total Amount (SAR)"]',
    )  # fmt: skip
    table = result.data["tables"][0]
    assert table["match_count"] == len([item for item in BOQ_PHASE1_ITEMS if item[5] > MILLION])
    assert "[" not in str(table["rows"][0])


def test_query_table_with_a_column_value_shorthand(context):
    item = BOQ_PHASE1_ITEMS[0]
    result = query_table(context, "BOQ_Phase1.xlsx", "BOQ", {"Item": str(item[0])})
    assert result.data["tables"][0]["match_count"] == 1
