"""Does a message continue the previous answer ("write that in Arabic", "w l tene?", "ترجم الجواب")?

Used only when the router model is not available and there is chat history: then numbers from the earlier
answer may be reused. A new question is never a follow-up, so its numbers must come from the tools again.
"""

import re

from AI.language.arabic_normalizer import normalize_arabic

FOLLOW_UP_WORDS = re.compile(
    r"\b(translate|in arabic|in english|write (it|that|this|them)|shorten|make it shorter|summari[sz]e (it|that)"
    r"|that answer|this answer|your answer|the answer|the (first|second|third|last) one|and the (first|second|other)"
    r"|same (table|list|answer)|those (items|numbers|dates)|what about the)\b"
    r"|ترجم|بالعربي|بالانجليزي|بالانكليزي|الجواب|جوابك|هيدا|هيدي|هيدول|والتاني|والثاني|نفس الجدول|اختصر"
    r"|\b(tarjem|tarjemle|bel 3arabe|bel 3arabi|bel english|bel engliziye|hayda|haydi|haydol|w l tene|w l tenye"
    r"|l jaweb|nafs l)\b",
    re.IGNORECASE,
)
MAX_FOLLOW_UP_WORDS = 14  # a long message is a new question even if it says "the answer"


def looks_like_follow_up(text: str) -> bool:
    words = text.split()
    return 0 < len(words) <= MAX_FOLLOW_UP_WORDS and bool(FOLLOW_UP_WORDS.search(normalize_arabic(text)))
