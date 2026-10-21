"""Turn money and number text like "SAR 1,250,000.00", "1.2M" or "(500)" into numbers."""

import math
import re

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٫٬", "01234567890123456789.,")

# Words with letters only are matched as whole words; symbols are matched anywhere.
CURRENCY_WORDS = {
    "SAR": ["sar", "s.r.", "sr", "ر.س", "ريال", "riyal", "riyals"],
    "USD": ["usd", "us$", "$", "dollar", "dollars", "دولار"],
    "EUR": ["eur", "€", "euro", "euros", "يورو"],
    "AED": ["aed", "dirham", "dirhams", "درهم"],
    "GBP": ["gbp", "£"],
    "EGP": ["egp", "جنيه"],
}

# Latin + Arabic letters (U+0600 to U+06FF), used to find whole words.
WORD_LETTERS = "a-z" + chr(0x0600) + "-" + chr(0x06FF)

MULTIPLIERS = {
    "k": 1e3,
    "thousand": 1e3,
    "ألف": 1e3,
    "m": 1e6,
    "mn": 1e6,
    "mm": 1e6,
    "million": 1e6,
    "مليون": 1e6,
    "b": 1e9,
    "bn": 1e9,
    "billion": 1e9,
    "مليار": 1e9,
}

NUMBER_WITH_SUFFIX = re.compile(r"^([0-9.,]+)(\s*)([" + WORD_LETTERS + r"]*)$")
SHORT_SUFFIXES = {"k", "m", "b"}  # only right after the number: "1.2M" yes, "150 m" (meters) no


PLAIN_NUMBER = re.compile(r"-?\d+(\.\d+)?")  # fast path: most cells are already plain numbers


def word_pattern(words: list[str]) -> str:
    """Latin words must stand alone ("sar" but not "sars"); symbols like "$" and Arabic words match anywhere,
    because Arabic joins prefixes to words ("بالدولار" = "in dollars"). Longest first."""
    parts = [
        rf"(?<![{WORD_LETTERS}]){re.escape(word)}(?![{WORD_LETTERS}])"
        if word.isalpha() and word.isascii()
        else re.escape(word)
        for word in sorted(words, key=len, reverse=True)
    ]
    return "|".join(parts)


# Built once: building regexes for every cell made big sheets slow.
CURRENCY_PATTERNS = {code: re.compile(word_pattern(words)) for code, words in CURRENCY_WORDS.items()}
ANY_CURRENCY = re.compile(word_pattern([word for words in CURRENCY_WORDS.values() for word in words]))


def detect_currency(text: str) -> str | None:
    """Return a currency code ("SAR", "USD", ...) mentioned in the text, or None."""
    lowered = str(text).lower()
    return next((code for code, pattern in CURRENCY_PATTERNS.items() if pattern.search(lowered)), None)


def currency_in_notes(texts: list[str]) -> str | None:
    """The one currency named in title or note text ("All prices are in US Dollars"). None when the notes
    name no currency or several, because then they do not say which column is in which."""
    found = {code for text in texts if (code := detect_currency(text))}
    return found.pop() if len(found) == 1 else None


def strip_currency(text: str) -> str:
    """Remove currency words and symbols from the text."""
    return ANY_CURRENCY.sub(" ", text)


def normalize_separators(digits: str) -> str | None:
    """Turn "1,250,000.50" or "1.250.000,50" into "1250000.50". None if not a number."""
    if digits.count(".") > 1 and "," not in digits:
        return digits.replace(".", "") if re.fullmatch(r"\d{1,3}(\.\d{3})+", digits) else None
    if "," in digits and "." in digits:
        if digits.rfind(",") > digits.rfind("."):  # European: 1.250.000,50
            digits = digits.replace(".", "").replace(",", ".")
        else:
            digits = digits.replace(",", "")
    elif "," in digits:
        if re.fullmatch(r"\d{1,3}(,\d{3})+", digits):
            digits = digits.replace(",", "")
        elif re.fullmatch(r"\d+,\d{1,2}", digits):  # decimal comma: 12,5
            digits = digits.replace(",", ".")
        else:
            return None
    return digits if re.fullmatch(r"\d+(\.\d+)?|\.\d+", digits) else None


def parse_number(value: object) -> float | None:
    """Return the number in the value, or None when it is not a plain number or amount."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return None if math.isnan(value) else float(value)

    text = str(value).translate(ARABIC_DIGITS).strip().lower()
    if not text:
        return None
    if PLAIN_NUMBER.fullmatch(text):
        return float(text)
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    text = strip_currency(text).replace("%", " ")
    text = re.sub(r"(?<=\d)[\s'](?=\d{3}\b)", "", text).strip()  # "1 250 000" -> "1250000"
    if text.startswith(("-", "−")):
        negative = not negative
        text = text[1:].strip()

    match = NUMBER_WITH_SUFFIX.match(text)
    if not match:
        return None
    digits, space, suffix = match.groups()
    if suffix and (suffix not in MULTIPLIERS or (space and suffix in SHORT_SUFFIXES)):
        return None
    normalized = normalize_separators(digits)
    if normalized is None:
        return None
    number = float(normalized) * MULTIPLIERS.get(suffix, 1)
    return -number if negative else number
