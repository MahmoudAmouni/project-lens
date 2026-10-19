"""Make Arabic text comparable: small spelling differences (hamza, ta marbuta, diacritics, digits) still match.

Used on the question and on document text before keyword search, and for money words in filters.
"""

import re

ARABIC_LETTERS = chr(0x0600) + "-" + chr(0x06FF)
# Diacritics (tashkeel, U+064B to U+0652, and the dagger alef U+0670) and tatweel (U+0640): removed.
DIACRITICS = re.compile("[" + chr(0x064B) + "-" + chr(0x0652) + chr(0x0670) + chr(0x0640) + "]")
LETTERS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ة": "ه", "ى": "ي"})
DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٫٬", "01234567890123456789.,")

MONEY_WORDS = {
    "ألف": 1e3, "alf": 1e3, "k": 1e3, "thousand": 1e3,
    "مليون": 1e6, "ملايين": 1e6, "malyon": 1e6, "malayin": 1e6, "million": 1e6, "m": 1e6, "mn": 1e6,
    "مليار": 1e9, "milyar": 1e9, "billion": 1e9, "b": 1e9, "bn": 1e9,
}  # fmt: skip
MONEY = re.compile(r"^(\d+(?:\.\d+)?)?\s*([a-z" + ARABIC_LETTERS + r"]+)$")


def normalize_arabic(text: str) -> str:
    """Lower case, no diacritics or tatweel, one form of alef / ta marbuta / ya, Western digits."""
    return DIACRITICS.sub("", str(text)).translate(LETTERS).translate(DIGITS).lower()


NORMALIZED_MONEY_WORDS = {normalize_arabic(word): value for word, value in MONEY_WORDS.items()}


def money_value(text: str) -> float | None:
    """ "مليون" -> 1000000, "2 مليون" -> 2000000, "malyon" -> 1000000, "1.5m" -> 1500000; None otherwise."""
    match = MONEY.match(normalize_arabic(text).replace(",", "").strip())
    if not match or match.group(2) not in NORMALIZED_MONEY_WORDS:
        return None
    return float(match.group(1) or 1) * NORMALIZED_MONEY_WORDS[match.group(2)]
