"""Keyword help for search: exact words catch what embeddings miss (rare terms, near-identical pages).

Arabic text is normalized on both sides, so "أعمال" matches "اعمال"; project words are added in the other
language ("facade" also searches "الواجهات").
"""

import re

from AI.language.arabic_normalizer import normalize_arabic
from AI.language.glossary import related_terms

STOP_WORDS = {
    "the", "and", "for", "with", "what", "are", "is", "of", "in", "on", "to", "a", "an", "all", "any", "from",
    "this", "that", "which", "how", "much", "many", "list", "show", "give", "about", "there", "per",
    "في", "من", "على", "إلى", "الى", "عن", "ما", "هي", "هو", "كم", "التي", "الذي", "مع", "شو", "يلي", "بدي",
    "shu", "yalli", "men", "aktar", "baddi", "fi", "bel", "kel", "w",
}  # fmt: skip
NORMALIZED_STOP_WORDS = {normalize_arabic(word) for word in STOP_WORDS}
KEYWORD_WEIGHT = 0.35  # a passage with every keyword gets +0.35 on its similarity score


def keywords(query: str) -> list[str]:
    """Meaningful words of the query plus their project translations, longest first."""
    words = {
        word
        for word in re.findall(r"\w+", query.lower())
        if len(word) >= 3 and normalize_arabic(word) not in NORMALIZED_STOP_WORDS
    }
    words.update(term.lower() for term in related_terms(query))
    return sorted(words, key=len, reverse=True)


def keyword_bonus(text: str, words: list[str]) -> float:
    """Share of the keywords that appear in the text (Arabic normalized), times KEYWORD_WEIGHT."""
    if not words:
        return 0.0
    normalized = normalize_arabic(text)
    return KEYWORD_WEIGHT * sum(normalize_arabic(word) in normalized for word in words) / len(words)
