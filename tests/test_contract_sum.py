"""'Contract sum' always means the amount the contract states, never a BOQ total (no API calls)."""

import pytest

from AI.language.glossary import related_terms
from AI.messages import build_messages
from AI.question_notes import CONTRACT_SUM_NOTE, asks_for_contract_sum, question_with_notes
from AI.router import Route


@pytest.mark.parametrize(
    "question",
    ["How much is retained on the full contract sum?", "What is the contract value?", "contract price?",
     "ما هي قيمة العقد؟", "قديش مبلغ العقد؟", "ade l 3a2ed?", "What is the accepted contract amount?"],
)  # fmt: skip
def test_contract_sum_questions_get_the_note(question):
    assert asks_for_contract_sum(question)
    assert CONTRACT_SUM_NOTE in question_with_notes(question, Route(style="en", intent="document_question"))


@pytest.mark.parametrize("question", ["What is the BOQ total?", "List the contract dates", "Who signed the contract?"])
def test_other_questions_do_not(question):
    assert not asks_for_contract_sum(question)
    assert CONTRACT_SUM_NOTE not in question_with_notes(question, Route(style="en", intent="document_question"))


def test_the_router_english_rewrite_also_counts():
    assert asks_for_contract_sum("قديش الاحتجاز؟", "How much is retained on the contract sum?")


def test_searches_also_use_the_other_names_of_the_contract_sum():
    assert {"contract price", "contract value"} <= set(related_terms("what is the contract sum"))


def test_the_rule_is_in_every_request():
    system = build_messages("What is the contract sum?", [])[0]["content"]
    assert "Never use a BOQ total, a sum of BOQs or a payment schedule total in its place." in system
