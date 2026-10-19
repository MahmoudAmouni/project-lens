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
    "who r u", "who are u", "what are you called", "what should i call you",
    "min enta", "meen enta", "min inta", "meen inta", "مين حضرتك", "من أنت", "مين انتا",
}  # fmt: skip
NORMALIZED_GREETINGS = {normalize_arabic(text) for text in GREETINGS}
# "your name" in any wording ("what is ur name", "sho esmak enta", "شو اسمك؟"): the greeting reply says the name
YOUR_NAME_WORDS = {"esmak", "ismak", "esmik", "ismik", "esmek", "smak", "اسمك", "اسمكم", "شسمك"}
YOUR_WORDS = {"your", "ur", "yr", "you", "u"}
NAME_QUESTION_MAX_WORDS = 6  # longer messages may ask about a name in the documents


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
    """Only the whole message: "hi" is a greeting, "hi, list the BOQ items" is not. Asking the AI's name is too."""
    words = words_of(text)
    return " ".join(words) in NORMALIZED_GREETINGS or asks_for_my_name(words)


def asks_for_my_name(words: list[str]) -> bool:
    """A short message about "your name": "what is ur name", "sho esmak enta", "ما اسمك" (not "contractor name")."""
    if not words or len(words) > NAME_QUESTION_MAX_WORDS:
        return False
    found = set(words)
    return bool(found & YOUR_NAME_WORDS) or ("name" in found and bool(found & YOUR_WORDS))
