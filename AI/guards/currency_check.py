"""Every currency in an answer must come from the tools or the question, like its numbers.

A model may write "86,400,000 SAR" for a contract that says "AED 86,400,000": the number passes the number check,
the currency is invented. When the tools used exactly one currency, a wrong currency CODE is replaced by it
("SAR" -> "AED"). Otherwise (several currencies, or a word like "riyal"), a short note in the user's style says
which currency the documents use, so the user is never misled silently.
"""

import logging
import re

from AI.language.arabic_normalizer import normalize_arabic
from AI.language.replies import currency_note

logger = logging.getLogger("projectlens")

# Currency -> how documents and answers write it (Latin words as whole words; Arabic also with ال / بال in front).
CURRENCY_NAMES = {
    "SAR": ["sar", "riyal", "riyals", "ر.س", "ريال", "ريالا", "ريالات"],
    "AED": ["aed", "dirham", "dirhams", "درهم", "دراهم"],
    "USD": ["usd", "us$", "dollar", "dollars", "دولار", "دولارات"],
    "EUR": ["eur", "euro", "euros", "€", "يورو"],
    "GBP": ["gbp", "£", "pound sterling", "جنيه استرليني"],
}
ARABIC_PREFIX = r"(?:(?:و|ب|ف|ل|ك)?ال|ب)?"  # "بالدرهم", "والريال"
CODE = re.compile(r"\b(SAR|AED|USD|EUR|GBP)\b")


def name_pattern(name: str) -> str:
    if re.search(r"[؀-ۿ]", name):
        return rf"(?<![؀-ۿ]){ARABIC_PREFIX}{re.escape(normalize_arabic(name))}(?![؀-ۿ])"
    return rf"(?<![a-z]){re.escape(name)}(?![a-z])"


PATTERNS = {code: re.compile("|".join(name_pattern(n) for n in names)) for code, names in CURRENCY_NAMES.items()}


def currencies_in(text: str) -> set[str]:
    """The currencies a text names: "AED 86,400,000" -> {"AED"}; "بالدرهم الإماراتي" -> {"AED"}."""
    plain = normalize_arabic(str(text)).lower()
    return {code for code, pattern in PATTERNS.items() if pattern.search(plain)}


def keep_tool_currencies(answer, known_texts: list[str], style: str):
    """Fix or flag a currency the answer names but no tool result (or the question) contains."""
    if answer.kind != "answer":
        return answer
    known = currencies_in(" ".join(map(str, known_texts)))
    wrong = sorted(currencies_in(answer.answer) - known)
    if not wrong or not known:
        return answer  # nothing invented, or the tools named no currency at all (nothing to compare with)
    logger.warning("Answer named currencies no tool returned: %s (tools: %s)", wrong, sorted(known))
    if len(known) == 1:  # one currency in the documents: "SAR" can safely become "AED"
        right = next(iter(known))
        answer.answer = CODE.sub(lambda match: right if match.group(1) in wrong else match.group(1), answer.answer)
        answer.steps.append(f"Corrected the currency to {right}, as in the documents")
        wrong = sorted(currencies_in(answer.answer) - known)
    if wrong:  # words like "riyal", or several currencies in the documents: say it plainly
        answer.answer += currency_note(sorted(known), wrong, style)
        answer.steps.append("Noted a currency the documents do not use")
    return answer
