"""Not-found answers name unreadable files, same-name files are flagged, not_found cannot hide made-up numbers."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from AI.agent import Agent
from AI.language.replies import fixed_reply, unreadable_note
from AI.tools.list_documents import document_overview, list_documents
from AI.tools.same_names import base_name, same_name_groups
from AI.tools.tool_context import ToolContext
from Server.ingestion.folder_loader import load_folder
from tests.fake_llm import FakeLLM, call, tool_reply

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_docs"


def document(name: str, status: str = "ok") -> SimpleNamespace:
    return SimpleNamespace(name=name, status=status, pages=[1], tables=[], message="", file_type="pdf")


@pytest.fixture(scope="module")
def documents():
    return load_folder(SAMPLE_DIR).documents


def not_found_reply(text: str) -> object:
    return tool_reply(call("submit_answer", {"answer": text, "kind": "not_found", "sources": []}))


def test_a_not_found_answer_names_the_unreadable_files(documents):
    unreadable = [d.name for d in documents if d.status != "ok"]
    answer = Agent(FakeLLM([not_found_reply("The VAT rate is not in the documents.")]), documents).ask("VAT rate?")
    assert answer.kind == "not_found"
    assert answer.answer.startswith("The VAT rate is not in the documents.")
    assert "These files could not be read" in answer.answer
    assert all(name in answer.answer for name in unreadable)


def test_the_note_follows_the_user_style_and_is_skipped_when_not_needed():
    files = [document("Contract.pdf"), document("Scan.pdf", "scanned")]
    assert unreadable_note("", files, "ar").startswith("\n\nتعذّرت قراءة هذه الملفات")
    assert "Scan.pdf (scanned)" in unreadable_note("", files, "ar")
    assert unreadable_note("Not found. Scan.pdf is a scan.", files, "en") == ""  # the answer already says it
    assert unreadable_note("", [document("Contract.pdf")], "en") == ""


def test_many_unreadable_files_are_cut_to_five():
    files = [document(f"Scan_{number}.pdf", "scanned") for number in range(8)]
    note = unreadable_note("", files, "en")
    assert "Scan_4.pdf" in note and "Scan_5.pdf" not in note and note.endswith("+3")


@pytest.mark.parametrize(
    ("name", "base"),
    [("old/Payment_Schedule.pdf", "payment_schedule.pdf"), ("Payment_Schedule (2).pdf", "payment_schedule.pdf"),
     ("Payment_Schedule - Copy.PDF", "payment_schedule.pdf"), ("BOQ_Phase2.xlsx", "boq_phase2.xlsx")],
)  # fmt: skip
def test_base_names_ignore_folders_and_copy_marks(name, base):
    assert base_name(name) == base


def test_same_name_files_are_flagged_in_the_overview_and_the_list():
    files = [document("Payment_Schedule.pdf"), document("old/Payment_Schedule.pdf"), document("BOQ_Phase1.pdf"),
             document("BOQ_Phase2.pdf")]  # fmt: skip
    assert same_name_groups([f.name for f in files]) == [["Payment_Schedule.pdf", "old/Payment_Schedule.pdf"]]
    overview = document_overview(files)
    assert "Files with the same name (maybe different versions): 'Payment_Schedule.pdf' and " in overview
    assert "BOQ_Phase1.pdf' and" not in overview
    listed = list_documents(ToolContext(documents=files)).data["documents"]
    assert listed[1]["same_name_as"] == ["Payment_Schedule.pdf"]
    assert "same_name_as" not in listed[2]


def test_the_same_name_note_survives_a_long_overview():
    files = [document(f"Report_{number:03}_with_a_long_name.pdf") for number in range(120)]
    files += [document("a/Notes.pdf"), document("b/Notes.pdf")]
    assert document_overview(files).endswith("point out where they disagree.")


def test_a_not_found_answer_with_made_up_numbers_gets_the_fixed_reply(documents):
    llm = FakeLLM([not_found_reply("Not in the files, but a typical VAT is 4,250,000 on this project.")])
    answer = Agent(llm, documents).ask("What is the VAT amount?")
    assert answer.kind == "not_found"
    assert answer.answer.startswith(fixed_reply("not_found", "en"))
    assert "4,250,000" not in answer.answer
