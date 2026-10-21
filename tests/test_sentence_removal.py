"""One made-up number costs one sentence, not the whole answer (the F4 / F6 live failures); no citation marks."""

from types import SimpleNamespace

from AI.guards.number_check import keep_tool_numbers, known_numbers, without_made_up_sentences
from AI.tools.submit_answer import without_history_tags

CONTRACT = "1.1 The Contract Sum is AED 86,400,000. 6.1 Each interim payment is due 45 days after certification."


def answer(text: str, table: dict | None = None) -> SimpleNamespace:
    return SimpleNamespace(kind="answer", answer=text, table=table, sources=[{"document": "Agreement.pdf"}], steps=[])


def test_only_the_sentence_with_the_made_up_number_goes():
    text = "The Contract Sum is AED 86,400,000. Payments are usually due within 28 days."
    assert without_made_up_sentences(text, known_numbers([CONTRACT])) == "The Contract Sum is AED 86,400,000."


def test_list_lines_and_arabic_sentences_are_checked_one_by_one():
    text = "قيمة العقد 86,400,000 درهم. المهلة 28 يوماً.\n- Payment: 45 days\n- Bonus: 2020 hours"
    kept = without_made_up_sentences(text, known_numbers([CONTRACT]))
    assert kept == "قيمة العقد 86,400,000 درهم.\n- Payment: 45 days"


def test_a_correct_answer_keeps_its_sources_and_loses_one_sentence():
    result = keep_tool_numbers(answer("The Contract Sum is AED 86,400,000. It is paid within 28 days."),
                               [CONTRACT], SimpleNamespace(saved_tables={}), [], "en")  # fmt: skip
    assert (result.kind, result.answer) == ("answer", "The Contract Sum is AED 86,400,000.")
    assert result.sources  # the sources of the true sentence stay
    assert result.steps == ["Removed a sentence with a number the tools did not return"]


def test_when_nothing_true_is_left_it_still_becomes_not_found():
    result = keep_tool_numbers(answer("It is 28 days."), [CONTRACT], SimpleNamespace(saved_tables={}), [], "en")
    assert result.kind == "not_found" and "28" not in result.answer


def test_a_typed_table_with_made_up_numbers_becomes_the_saved_rows_and_the_text_stays():
    saved = {"t1": {"columns": ["Item", "Amount", "Source"], "rows": [["A1", 156000, "BOQ.xlsx · BOQ · row 7"]]}}
    typed = {"columns": ["Item", "Amount", "Source"], "rows": [["A1", 999999, "BOQ.xlsx · BOQ · row 7"]]}
    result = keep_tool_numbers(answer("Item A1 costs SAR 156,000 in the BOQ.", typed), ["A1 156000"],
                               SimpleNamespace(saved_tables=saved), ["t1"], "en")  # fmt: skip
    assert result.answer == "Item A1 costs SAR 156,000 in the BOQ."
    assert result.table["rows"] == saved["t1"]["rows"]


def test_model_citation_marks_are_removed_from_the_text():
    text = "The Contract Sum is **AED 86,400,000**【source1】.\nTaken from page 4【4†L1-L3】."
    assert without_history_tags(text) == "The Contract Sum is **AED 86,400,000**.\nTaken from page 4."
