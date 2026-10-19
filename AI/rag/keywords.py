"""Keyword help for search: exact words catch what embeddings miss (rare terms, near-identical pages)."""

import re

STOP_WORDS = {
    "the", "and", "for", "with", "what", "are", "is", "of", "in", "on", "to", "a", "an", "all", "any", "from",
    "this", "that", "which", "how", "much", "many", "list", "show", "give", "about", "there", "per",
    "في", "من", "على", "إلى", "الى", "عن", "ما", "هي", "هو", "كم", "التي", "الذي", "مع",
}  # fmt: skip
KEYWORD_WEIGHT = 0.35  # a passage with every keyword gets +0.35 on its similarity score


def keywords(query: str) -> list[str]:
    """Meaningful words of the query, longest first."""
    words = {word for word in re.findall(r"\w+", query.lower()) if len(word) >= 3 and word not in STOP_WORDS}
    return sorted(words, key=len, reverse=True)


def keyword_bonus(text: str, words: list[str]) -> float:
    """Share of the keywords that appear in the text, times KEYWORD_WEIGHT."""
    if not words:
        return 0.0
    lowered = text.lower()
    return KEYWORD_WEIGHT * sum(word in lowered for word in words) / len(words)
