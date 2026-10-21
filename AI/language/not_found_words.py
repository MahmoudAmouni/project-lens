"""Does an answer say the information was not found? Models sometimes write that as a normal answer
(kind "answer") instead of kind "not_found", and then the note about unreadable files would be lost.
"""

import re

from AI.language.arabic_normalizer import normalize_arabic

NOT_FOUND_WORDS = re.compile(
    r"\b(could ?n[o']t|can ?n?[o']t|did ?n[o']t|was unable to|unable to) (find|locate|confirm|determine|retrieve)\b"
    r"|\bno (information|mention|data|record|details?) (on|about|for|of|regarding)\b"
    r"|\b(is|are|was|were) not (mentioned|stated|specified|given|found|available|included)\b"
    r"|\bnot found in\b"
    r"|لم اجد|لم يتم العثور|لا يوجد|لا توجد|غير موجود|غير مذكور|ما لقيت|مش موجود|مش مذكور"
    r"|\b(ma la2et|ma l2it|mesh mawjoud|msh mawjoud|mish mawjoud)\b",
    re.IGNORECASE,
)


def says_not_found(answer_text: str) -> bool:
    """True for "I could not find...", "is not mentioned", "لم أجد", "ما لقيت", "ma la2et"..."""
    return bool(NOT_FOUND_WORDS.search(normalize_arabic(answer_text or "")))


NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
FIRST_SENTENCE = re.compile(r"^.*?(?:[.!?؟](?:\s|$)|\n|$)", re.DOTALL)


def opens_with_not_found(answer_text: str, question: str = "") -> bool:
    """True when the whole answer is a "not found": its first sentence says so and it gives no number of its own.
    "Retention is 5%. The excess is not mentioned." and "Not found, but the cap is 10%." found something."""
    first = FIRST_SENTENCE.match((answer_text or "").strip())
    new_numbers = set(NUMBER.findall(answer_text or "")) - set(NUMBER.findall(question or ""))
    return bool(first) and says_not_found(first.group(0)) and not new_numbers
