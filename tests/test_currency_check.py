"""A currency the answer names but no tool returned is corrected (one currency) or flagged (no API calls)."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from AI.agent import Agent
from AI.guards.currency_check import currencies_in, keep_tool_currencies
from Server.ingestion.folder_loader import load_folder
from tests.fake_llm import FakeLLM, call, tool_reply

CONTRACT_PAGE = '{"matches": [{"text": "1.1 The Contract Sum is AED 86,400,000 (UAE Dirhams), excluding VAT."}]}'


def answer(text: str, kind: str = "answer") -> SimpleNamespace:
    return SimpleNamespace(answer=text, kind=kind, steps=[])


@pytest.mark.parametrize(
    ("text", "codes"),
    [("AED 86,400,000", {"AED"}), ("86,400,000 SAR", {"SAR"}), ("جميع الأسعار بالدرهم الإماراتي", {"AED"}),
     ("مبلغ 5,000 ريال", {"SAR"}), ("5,000 dollars and EUR 300", {"USD", "EUR"}), ('"currency": "AED"', {"AED"}),
     ("SARA said the user", set()), ("12 items", set())],
)  # fmt: skip
def test_currencies_in_texts(text, codes):
    assert currencies_in(text) == codes


def test_a_wrong_code_becomes_the_one_currency_of_the_documents():
    fixed = keep_tool_currencies(answer("The Contract Sum is 86,400,000 SAR."), ["contract sum?", CONTRACT_PAGE], "en")
    assert fixed.answer == "The Contract Sum is 86,400,000 AED."
    assert "Corrected the currency to AED" in fixed.steps[0]


def test_a_wrong_currency_word_gets_a_note_in_the_user_style():
    fixed = keep_tool_currencies(answer("قيمة العقد 86,400,000 ريال."), ["قيمة العقد؟", CONTRACT_PAGE], "ar")
    assert fixed.answer.startswith("قيمة العقد 86,400,000 ريال.")
    assert "AED" in fixed.answer and "ملاحظة" in fixed.answer


def test_with_several_document_currencies_a_wrong_one_is_flagged_not_guessed():
    texts = ["totals?", CONTRACT_PAGE, '{"sums": {"Total (USD)": {"sum": 624350, "currency": "USD"}}}']
    fixed = keep_tool_currencies(answer("The total is 624,350 SAR."), texts, "en")
    assert "624,350 SAR" in fixed.answer  # not silently changed to one of two possible currencies
    assert "Note: the documents give these amounts in AED / USD; SAR does not appear in them." in fixed.answer


@pytest.mark.parametrize(
    ("text", "texts"),
    [("The Contract Sum is AED 86,400,000.", ["contract sum?", CONTRACT_PAGE]),  # right currency
     ("Convert it to SAR please: 86,400,000 AED.", ["in SAR?", CONTRACT_PAGE]),  # the user named SAR
     ("The total is 86,400,000 SAR.", ["total?", '{"rows": [[1, 86400000]]}'])],  # tools named no currency
)  # fmt: skip
def test_answers_are_left_alone_when_nothing_is_invented(text, texts):
    assert keep_tool_currencies(answer(text), texts, "en").answer == text


def test_fixed_replies_are_not_checked():
    reply = answer("I couldn't find this in the loaded documents.", kind="not_found")
    assert keep_tool_currencies(reply, [CONTRACT_PAGE], "en") is reply


def test_the_agent_corrects_a_currency_the_contract_does_not_use():
    documents = load_folder(Path(__file__).resolve().parent.parent / "sample_docs").documents
    read = tool_reply(call("read_document", {"document": "Contract_A.pdf", "start_page": 1, "end_page": 1}))
    source = {"document": "Contract_A.pdf", "page": 1}
    submit = tool_reply(call("submit_answer", {"answer": "The contract price is USD 64,500,000.", "sources": [source]}))
    result = Agent(FakeLLM([read, submit]), documents).ask("What is the contract price?")
    assert result.answer == "The contract price is SAR 64,500,000."
