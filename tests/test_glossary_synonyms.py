"""Synonyms: "rate" finds a "Unit Price" column, "LDs" searches "liquidated damages"; Groq runs at temperature 0."""

from types import SimpleNamespace

import pandas as pd
import pytest

from AI.language.glossary import related_terms, synonyms
from AI.llm_helpers import request_options
from AI.rag.keywords import keywords
from AI.tools.lookup import find_column


def table(*columns: str) -> SimpleNamespace:
    return SimpleNamespace(id="BOQ", data=pd.DataFrame(columns=list(columns)))


@pytest.mark.parametrize(
    ("wanted", "column"),
    [("rate", "Unit Price"), ("unit rate", "Unit Price"), ("quantity", "Qty"), ("uom", "Unit"),
     ("particulars", "Description"), ("amount", "Total Price")],
)  # fmt: skip
def test_a_synonym_finds_the_real_column(wanted, column):
    assert find_column(table("Item", "Description", "Unit", "Qty", "Unit Price", "Total Price"), wanted) == column


def test_a_close_name_still_wins_over_a_synonym():
    assert find_column(table("Item", "Unit Rate (SAR)", "Total Amount (SAR)"), "rate") == "Unit Rate (SAR)"
    assert find_column(table("Item", "Unit Rate (SAR)", "Total Amount (SAR)"), "amount") == "Total Amount (SAR)"


def test_unknown_words_have_no_synonyms():
    assert synonyms("concrete") == []
    assert "unit price" in synonyms(" Rate ")


def test_contract_abbreviations_widen_the_text_search():
    assert "liquidated damages" in related_terms("What are the LDs?")
    assert "extension of time" in keywords("how many days of EOT were granted")
    assert related_terms("the developer will deliver") == []  # "dlp" is not inside "developer"


def test_column_words_do_not_dilute_the_text_search():
    assert "unit price" not in keywords("what is the rate of concrete")


def test_groq_runs_at_temperature_zero_and_gemini_keeps_its_default():
    assert request_options("openai/gpt-oss-120b", [], "auto", False, None, "medium")["temperature"] == 0
    assert "temperature" not in request_options("gemini-3.5-flash", [], "auto", False, None, "medium")
