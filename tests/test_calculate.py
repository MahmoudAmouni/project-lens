"""The calculate tool does exact arithmetic, but only on numbers the tools returned or the question gave."""

from pathlib import Path

import pytest

from AI.agent import Agent
from AI.tools.calculate import calculate
from AI.tools.tool_context import ToolContext, ToolError
from Server.ingestion.folder_loader import load_folder
from tests.fake_llm import FakeLLM, call, tool_reply

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_docs"
TOOL_RESULT = '{"sums": {"Total Amount (SAR)": {"sum": 26917500}}, "Unit Rate": 5600, "Qty": 1150, "Amount": 6440000}'


def context_with(*texts: str) -> ToolContext:
    return ToolContext(documents=[], known_texts=list(texts))


@pytest.mark.parametrize(
    ("expression", "result"),
    [("26917500 * 15 / 100", 4037625), ("26,917,500 * 15%", 4037625), ("5600 * 1150", 6440000),
     ("(26917500 - 6440000) / 2", 10238750), ("٥٦٠٠ × 1150", 6440000), ("-5600 + 1150", -4450)],
)  # fmt: skip
def test_arithmetic_on_tool_numbers_is_exact(expression, result):
    data = calculate(context_with(TOOL_RESULT, "What is 15% of it?"), expression).data
    assert data["result"] == result


def test_a_share_is_rounded_to_two_decimals_too():
    data = calculate(context_with(TOOL_RESULT), "6440000 / 26917500 * 100").data
    assert data["result"] == 23.925 and data["result_rounded"] == 23.92


def test_numbers_no_tool_returned_are_refused():
    with pytest.raises(ToolError, match="not returned by any tool"):
        calculate(context_with(TOOL_RESULT), "26917500 * 1.15 + 250000")


@pytest.mark.parametrize(
    "expression",
    ["__import__('os').system('dir')", "2 ** 1000", "abs(-5600)", "[5600, 1150]", "5600 % 3", "x * 2", "True + 1"],
)
def test_anything_but_plain_arithmetic_is_refused(expression):
    with pytest.raises(ToolError):
        calculate(context_with(TOOL_RESULT), expression)


def test_division_by_zero_and_bad_text_give_clear_errors():
    with pytest.raises(ToolError, match="Division by zero"):
        calculate(context_with(TOOL_RESULT), "5600 / 0")
    with pytest.raises(ToolError, match="not a valid expression"):
        calculate(context_with(TOOL_RESULT), "5600 * * ")
    with pytest.raises(ToolError, match="Give an expression"):
        calculate(context_with(TOOL_RESULT), " ")


def test_the_agent_keeps_a_calculated_number_in_its_answer():
    documents = load_folder(SAMPLE_DIR).documents
    query = call("query_table", {"document": "BOQ_Phase1.xlsx", "table_id": "BOQ",
                                 "filters": [{"column": "amount", "operator": ">", "value": 1000000}]})  # fmt: skip
    vat = call("calculate", {"expression": "26917500 * 15%", "label": "VAT on the items"})
    submit = call("submit_answer", {"answer": "VAT at 15% on **SAR 26,917,500** is **SAR 4,037,625**.",
                                    "sources": [{"document": "BOQ_Phase1.xlsx", "location": "Sheet BOQ"}]})  # fmt: skip
    llm = FakeLLM([tool_reply(query), tool_reply(vat), tool_reply(submit)])
    answer = Agent(llm, documents).ask("What is 15% VAT on the items above SAR 1 million?")
    assert "4,037,625" in answer.answer
    assert "Calculated VAT on the items" in answer.steps


def test_the_agent_cannot_calculate_with_a_number_it_made_up():
    llm = FakeLLM([tool_reply(call("calculate", {"expression": "5000000 * 15%"}))])
    agent = Agent(llm, [])
    agent.tool_texts = ["What is the VAT?", ""]
    agent.context.known_texts = agent.tool_texts
    outcome_messages = []
    agent.run_tools(llm.complete([], []), outcome_messages, [])
    assert "not returned by any tool" in outcome_messages[-1]["content"]
