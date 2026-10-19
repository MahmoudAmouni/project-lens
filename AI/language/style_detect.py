"""Guess the user's writing style without the AI: the router's fail-safe, and a check on the router's answer.

Styles: "en" English, "ar" Modern Standard Arabic, "ar-lb" Lebanese in Arabic letters, "arabizi" Latin letters.
"""

import re

from AI.language.arabic_normalizer import ARABIC_LETTERS, normalize_arabic
from AI.language.glossary import ARABIZI, LEBANESE_MARKERS

ARABIC_CHAR = re.compile(f"[{ARABIC_LETTERS}]")
LATIN_CHAR = re.compile("[a-zA-Z]")
ARABIC_PUNCTUATION = re.compile("[،؛؟٪-٭۔]")  # ، ؛ ؟ ٪ ٫ ٬ ٭ ۔
DIGIT_AS_LETTER = re.compile(r"^[a-z]*[235789][a-z]+$|^[a-z]+[235789][a-z]*$")  # 3a2ed, la5asli, mar7aba
NUMBER_WITH_UNIT = re.compile(r"^\d+(st|nd|rd|th|m|mm|cm|km|m2|m3|k|kg|t|mn|bn|kva|tr)$")  # "2nd", "5m": English
NORMALIZED_MARKERS = {normalize_arabic(word) for word in LEBANESE_MARKERS}
GREETINGS = {
    "hi", "hello", "hey", "thanks", "thank you", "good morning", "who are you", "what can you do",
    "marhaba", "mar7aba", "ahla", "ahlan", "kifak", "kifik", "salam", "merci", "shukran", "yislamo",
    "مرحبا", "اهلا", "أهلا", "السلام عليكم", "شكرا", "كيفك", "مين انت", "من انت", "صباح الخير",
    # asking the AI its name: the greeting reply says it ("I'm ProjectLens" / "أنا بصيرة")
    "what is your name", "what s your name", "whats your name", "your name", "who r u", "who are u",
    "what are you called", "what should i call you",
    "shu esmak", "shu ismak", "shu esmik", "shou esmak", "chou esmak", "esmak", "ismak", "min enta", "meen enta",
    "شو اسمك", "ما اسمك", "ما هو اسمك", "اسمك", "شو اسمك انت", "اسمك شو", "مين حضرتك", "من أنت",
}  # fmt: skip
NORMALIZED_GREETINGS = {normalize_arabic(text) for text in GREETINGS}


def words_of(text: str) -> list[str]:
    """Words only: Arabic punctuation (؟ ، ؛) sits in the Arabic letter range, so it is removed first."""
    return re.findall(rf"[a-z0-9{ARABIC_LETTERS}]+", ARABIC_PUNCTUATION.sub(" ", normalize_arabic(text)))


def arabizi_score(words: list[str]) -> int:
    return sum(
        word in ARABIZI or (bool(DIGIT_AS_LETTER.match(word)) and not NUMBER_WITH_UNIT.match(word)) for word in words
    )


def detect_style(text: str, ui_language: str | None = None) -> str:
    """Best guess of the style from the letters and words used."""
    words = words_of(text)
    arabic, latin = len(ARABIC_CHAR.findall(text)), len(LATIN_CHAR.findall(text))
    if arabic > latin:
        return "ar-lb" if NORMALIZED_MARKERS & set(words) else "ar"
    score = arabizi_score(words)
    if score >= 2 or (score >= 1 and len(words) <= 3):
        return "arabizi"
    if ui_language == "ar" and len(words) <= 2:  # "BOQ?" typed on the Arabic screen
        return "ar"
    return "en"


def looks_like_greeting(text: str) -> bool:
    """Only the whole message: "hi" is a greeting, "hi, list the BOQ items" is not."""
    return " ".join(words_of(text)) in NORMALIZED_GREETINGS
