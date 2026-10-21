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
