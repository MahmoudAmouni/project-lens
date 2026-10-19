"""Regular expressions for dates in project documents (English, Arabic and Hijri), and time periods."""

import re

DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

EN_MONTHS = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?"
    r"|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)
AR_MONTHS = (
    r"(?:يناير|فبراير|مارس|أبريل|ابريل|مايو|يونيو|يوليو|أغسطس|اغسطس|سبتمبر|أكتوبر|اكتوبر|نوفمبر|ديسمبر"
    r"|محرم|صفر|ربيع الأول|ربيع الآخر|جمادى الأولى|جمادى الآخرة|رجب|شعبان|رمضان|شوال|ذو القعدة|ذو الحجة)"
)
DAY = r"(?:[0-3]?\d)(?:st|nd|rd|th)?"
YEAR = r"(?:1[34]\d\d|20\d\d)"  # Hijri years 13xx-14xx, Gregorian 20xx

DATE_PATTERNS = [
    ("date", rf"\b{DAY}\s+{EN_MONTHS}\.?,?\s+{YEAR}\b"),  # 12 January 2026
    ("date", rf"\b{EN_MONTHS}\.?\s+{DAY},?\s+{YEAR}\b"),  # January 12, 2026
    ("date", rf"\b{YEAR}[-/.](?:0?[1-9]|1[0-2])[-/.](?:0?[1-9]|[12]\d|3[01])\b"),  # 2026-01-12, 1447/03/12
    ("date", rf"\b(?:0?[1-9]|[12]\d|3[01])[-/.](?:0?[1-9]|1[0-2])[-/.]{YEAR}\b"),  # 12/01/2026
    ("date", rf"{DAY}\s+{AR_MONTHS}\s+{YEAR}"),  # ١ فبراير ٢٠٢٦
    ("month", rf"\b{EN_MONTHS}\s+{YEAR}\b"),  # March 2028
    ("quarter", rf"\b(?:Q[1-4]|H[12])\s*[-/]?\s*{YEAR}\b"),  # Q3 2026, H1 2027
    ("hijri", rf"\b{YEAR}\s*(?:H|AH|هـ)\b"),  # 1447H, 1447 هـ
]
NUMBER_WORD = r"(?:\d+|one|two|three|four|six|twelve)"
UNIT = r"(?:calendar\s+|working\s+|business\s+)?(?:days?|weeks?|months?|years?)"
PERIOD_PATTERNS = [
    ("period", rf"\b(?:within|after|before|by|for|each|every)\s+{NUMBER_WORD}\s+{UNIT}\b"),  # within 28 days
    ("period", rf"\b{NUMBER_WORD}\s+{UNIT}\s+(?:after|from|before|of)\b"),  # 12 months after
]

COMPILED = [(kind, re.compile(pattern, re.IGNORECASE)) for kind, pattern in [*DATE_PATTERNS, *PERIOD_PATTERNS]]


def find_date_mentions(text: str) -> list[tuple[str, str, int, int]]:
    """(kind, matched text, start, end) for every date or period in the text, without overlaps."""
    normalized = text.translate(DIGITS)  # same length, so positions match the original text
    found: list[tuple[str, str, int, int]] = []
    for kind, pattern in COMPILED:
        for match in pattern.finditer(normalized):
            start, end = match.span()
            if any(start < other_end and end > other_start for _, _, other_start, other_end in found):
                continue
            found.append((kind, " ".join(text[start:end].split()), start, end))
    return sorted(found, key=lambda item: item[2])


def sentence_around(text: str, start: int, end: int, width: int = 110) -> str:
    """The sentence (or line) around a match, shortened to about `width` characters each side."""
    left = max(text.rfind("\n", 0, start), text.rfind(". ", 0, start))
    left = max(left + 1, start - width)
    right_candidates = [i for i in (text.find("\n", end), text.find(". ", end)) if i != -1]
    right = min([*right_candidates, end + width])
    return " ".join(text[left : right + 1].split())
