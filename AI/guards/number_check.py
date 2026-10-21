"""Numbers in an answer must come from the tools: the last check against made-up rows and amounts.

Every number in the answer text must match a number the tools returned, the question or the chat history.
Plain numbers must match exactly; scaled ones may be rounded ("1.2 million" for 1,176,000).
Small numbers (below 10) are not checked: they are counts, pages and list numbers."""

import logging
import math
import re

from AI.language.replies import fixed_reply
from AI.tools.saved_tables import combine_saved_tables

logger = logging.getLogger("projectlens")

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٬٫", "01234567890123456789,.")
NUMBER = re.compile(  # item codes ("C40", "2.2.1") are not numbers; "1.2M", "5mil" and "3 million" are scaled
    r"(?<![\w.])(\d+(?:,\d{3})*(?:\.\d+)?)(?![\d.]\d)"
    r"(?:(k|m)\b|\s?(mn|bn|mil|mill)\b"
    r"|\s*(thousands?|millions?|billions?|ألف|الف|آلاف|الاف|مليون|ملايين|مليار|مليارات|malyon|malayin|alf)(?!\w))?",
    re.IGNORECASE,
)
SCALE = {
    "k": 1e3, "thousand": 1e3, "thousands": 1e3, "ألف": 1e3, "الف": 1e3, "آلاف": 1e3, "الاف": 1e3, "alf": 1e3,
    "m": 1e6, "mn": 1e6, "mil": 1e6, "mill": 1e6, "million": 1e6, "millions": 1e6, "مليون": 1e6, "ملايين": 1e6,
    "malyon": 1e6, "malayin": 1e6,
    "bn": 1e9, "billion": 1e9, "billions": 1e9, "مليار": 1e9, "مليارات": 1e9,
}  # fmt: skip
# "above a million", "aktar men malyon", "أكثر من مليون": the scale word alone means one of it.
SCALE_WORD_ALONE = re.compile(r"(?<![\d\w])(thousand|million|billion|ألف|مليون|مليار|malyon|alf)(?!\w)", re.IGNORECASE)
SMALLEST_CHECKED = 10
SENTENCE_END = re.compile(r"(?<=[.!?؟])\s+")
MIN_KEPT_CHARS = 25  # less than this left after removing made-up sentences is not an answer any more


def numbers_in(text: str) -> list[tuple[float, float, int | None]]:
    """(value, value without its scale word, significant digits or None when it must match exactly)."""
    found = []
    for match in NUMBER.finditer(str(text).translate(ARABIC_DIGITS)):
        written = match.group(1)
        plain = float(written.replace(",", ""))
        scale = SCALE.get((match.group(2) or match.group(3) or match.group(4) or "").lower(), 1)
        digits = written.replace(",", "").replace(".", "").strip("0") if scale != 1 else ""
        found.append((plain * scale, plain, max(len(digits), 1) if digits else None))
    return found


def round_to(value: float, digits: int) -> float:
    if value == 0:
        return 0.0
    return round(value, digits - 1 - math.floor(math.log10(abs(value))))


def is_known(value: float, digits: int | None, known: set[float]) -> bool:
    """True when the number, or (for a scaled number) a rounded form of it, is one the tools returned."""
    if value in known:
        return True
    return digits is not None and any(math.isclose(round_to(number, digits), value) for number in known)


def known_numbers(texts: list[str]) -> set[float]:
    """Every number in what the tools returned, the question and the history ("a million" counts as 1,000,000)."""
    found = {value for text in texts for value, _, _ in numbers_in(text)}
    found.update(SCALE[word.lower()] for text in texts for word in SCALE_WORD_ALONE.findall(str(text)))
    return found


def unsupported_numbers(text: str, known: set[float]) -> list[float]:
    """The numbers in the text that no tool returned."""
    return [
        value
        for value, plain, digits in numbers_in(text)
        if abs(value) >= SMALLEST_CHECKED
        and not is_known(value, digits, known)
        and not is_known(plain, None, known)  # "1200 m" is metres, not 1,200 million
    ]


def table_text(table: dict | None) -> str:
    return " ".join(str(cell) for row in (table or {}).get("rows", []) for cell in row if cell is not None)


def without_made_up_sentences(text: str, known: set[float]) -> str:
    """The text without the sentences (or list lines) that hold a number no tool returned; the rest stays.
    "The Contract Sum is AED 86,400,000. Payment is due in 28 days." -> "The Contract Sum is AED 86,400,000."."""
    lines = []
    for line in text.splitlines():
        kept = " ".join(part for part in SENTENCE_END.split(line) if not unsupported_numbers(part, known))
        if kept.strip() or not line.strip():
            lines.append(kept)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def keep_tool_numbers(answer, known_texts: list[str], context, new_table_ids: list[str], style: str):
    """Numbers no tool returned never reach the user. Only the sentences holding them are removed when the rest
    still says something; a made-up table becomes the saved rows. When nothing useful is left, the exact saved
    rows are shown, or the fixed "not found" reply. A "not found" answer is checked too."""
    if answer.kind not in ("answer", "not_found"):
        return answer
    known = known_numbers([*known_texts, *(table_text(table) for table in context.saved_tables.values())])
    made_up = unsupported_numbers(f"{answer.answer} {table_text(answer.table)}", known)
    if not made_up:
        return answer
    logger.warning("Answer had numbers no tool returned: %s", made_up[:10])
    if answer.table and unsupported_numbers(table_text(answer.table), known):  # a typed table: use the saved rows
        answer.table = combine_saved_tables(context, new_table_ids[-1:]) if new_table_ids else None
        answer.steps.append("Replaced a table that had numbers the tools did not return")
    if not unsupported_numbers(answer.answer, known):
        return answer  # only the table was wrong, and it is replaced
    kept = without_made_up_sentences(answer.answer, known) if answer.kind == "answer" else ""
    if len(kept) >= MIN_KEPT_CHARS:  # the rest still answers: lose one sentence, not the whole answer
        answer.answer = kept
        answer.steps.append("Removed a sentence with a number the tools did not return")
        if new_table_ids and not answer.table:  # removed lines were often made-up rows: show the real ones
            answer.table = combine_saved_tables(context, new_table_ids[-1:])
        return answer
    answer.steps.append("Removed numbers the tools did not return")
    answer.sources = []
    if new_table_ids:
        answer.table = answer.table or combine_saved_tables(context, new_table_ids[-1:])
        answer.answer = fixed_reply("table_only", style)
    else:
        answer.kind, answer.table, answer.answer = "not_found", None, fixed_reply("not_found", style)
    return answer
