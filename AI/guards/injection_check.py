"""A plain check for prompt injection ("ignore your rules..."), so it is stopped even if the router misses it."""

import re

from AI.language.arabic_normalizer import normalize_arabic

INJECTION_PATTERNS = [
    r"\b(ignore|forget|disregard|bypass|override)\b.{0,30}\b(rules|instructions|prompt|guidelines|restrictions)\b",
    r"\b(system prompt|your prompt|developer mode|jailbreak|dan mode)\b",
    r"\b(you are now|act as|pretend (to be|you are)|role ?play)\b",
    r"(تجاهل|انس|انسى|تخط).{0,20}(التعليمات|القواعد|الاوامر)",
    r"\b(ignore|insa|tjehal)\b.{0,15}\b(l )?(rules|instructions|2awe3ed)\b",
]
INJECTION = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)


def looks_like_injection(text: str) -> bool:
    """True for messages that try to change the assistant's rules."""
    return bool(INJECTION.search(normalize_arabic(text)))
