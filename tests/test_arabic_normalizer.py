"""Arabic normalization, money words and the glossary."""

import pytest

from AI.language.arabic_normalizer import money_value, normalize_arabic
from AI.language.glossary import related_terms
from AI.rag.keywords import keyword_bonus, keywords
from AI.tools.table_filters import to_number


def test_normalize_unifies_letters_digits_and_removes_diacritics():
    assert normalize_arabic("أعمالُ الواجهاتـ") == "اعمال الواجهات"
    assert normalize_arabic("إجمالي القيمة مستشفى") == "اجمالي القيمه مستشفي"
    assert normalize_arabic("٢٥٠٠ و ۲٥۰۰") == "2500 و 2500"


@pytest.mark.parametrize(
    ("text", "value"),
    [("مليون", 1e6), ("2 مليون", 2e6), ("٣ مليون", 3e6), ("malyon", 1e6), ("1.5m", 1.5e6), ("ألف", 1e3),
     ("sar", None), ("10", None)],
)  # fmt: skip
def test_money_words(text, value):
    assert money_value(text) == value


@pytest.mark.parametrize("value", ["مليون ريال", "2 مليون ريالا", "malyon", "SAR 1M", "1,000,000", 1000000])
def test_filters_accept_arabic_and_arabizi_amounts(value):
    assert to_number(value) in (1e6, 2e6)


def test_keywords_search_both_languages_and_skip_dialect_grammar():
    words = keywords("shu l items yalli aktar men malyon bel BOQ")
    assert "جدول الكميات" in words and "million" in words
    assert not {"shu", "yalli", "men"} & set(words)
    assert "facade" in keywords("قيمة أعمال الواجهات")


def test_keyword_bonus_ignores_spelling_differences():
    assert keyword_bonus("تبلغ قيمة أعمال الواجهات", ["قيمه", "اعمال"]) == pytest.approx(0.35)


def test_related_terms_translate_project_words_both_ways():
    assert "نطاق العمل" in related_terms("la5asli l scope of work")
    assert "contractor" in related_terms("من هو المقاول؟")
