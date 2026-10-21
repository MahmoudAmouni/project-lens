"""The checks every document answer passes before the user sees it, in order:

clean history tags -> numbers must come from tools -> facts need sources -> a whole "not found" shows no sources
-> attach the saved rows the answer uses -> name the unreadable files when something was not found.
"""

from AI.guards.answer_check import check_answer
from AI.guards.number_check import keep_tool_numbers, known_numbers, table_text
from AI.language.not_found_words import opens_with_not_found, says_not_found
from AI.language.replies import fixed_reply, unreadable_note
from AI.tools.saved_tables import combine_saved_tables
from AI.tools.submit_answer import without_history_tags
from AI.tools.tool_context import ToolContext

MIN_SHARED_NUMBERS = 2  # the answer must quote at least this many of a table's numbers to show that table
SMALLEST_SHARED = 10  # counts and list numbers ("2.06", "3 items") do not tie an answer to a table


def uses_table(answer_text: str, table: dict) -> bool:
    """True when the answer quotes numbers from these rows: then the table shows the rows behind it.
    A table from a side search (lift drainage variations under an advance-payment answer) is left out."""
    in_answer = {value for value in known_numbers([answer_text]) if abs(value) >= SMALLEST_SHARED}
    in_table = known_numbers([table_text(table)])
    return len(in_answer & in_table) >= MIN_SHARED_NUMBERS


def finish_answer(answer, question: str, context: ToolContext, tool_texts: list[str], consulted: list, style: str):
    """Run every check on a document answer; returns the answer the user will see."""
    answer.answer = without_history_tags(answer.answer)  # plain-text replies skip submit_answer's cleaning
    answer = keep_tool_numbers(answer, tool_texts, context, list(context.saved_tables), style)
    answer = check_answer(answer, consulted, fixed_reply("not_found", style))
    if answer.kind == "answer" and not answer.table and opens_with_not_found(answer.answer, question):
        answer.kind, answer.sources = "not_found", []  # nothing was found: a searched file is not a source
    if answer.kind == "answer" and not answer.table and context.saved_tables:
        last = combine_saved_tables(context, list(context.saved_tables)[-1:])
        answer.table = last if uses_table(answer.answer, last) else None
    if answer.kind == "not_found" or says_not_found(answer.answer):  # it may be in an unreadable file: say which
        answer.answer += unreadable_note(answer.answer, context.documents, style)
    return answer
