"""The note added under the user's question: which style to answer in, and the question in both languages."""

import re

from AI.language.arabic_normalizer import normalize_arabic
from AI.router import Route

# No numbers in these examples: the model copied them into its answers ("14 items") instead of the tool's count.
STYLE_INSTRUCTIONS = {
    "en": "Reply in clear English.",
    "ar": "Reply in Modern Standard Arabic.",
    "ar-lb": "Reply in light, professional Lebanese Arabic written in Arabic letters "
    "(for example: في ... بند أكتر من مليون ريال، أكبرهن...).",
    "arabizi": "Reply in Lebanese Arabic written in Latin letters (Arabizi), like the user writes "
    "(for example: Fi ... items aktar men malyon SAR, akbar wehde...).",
}

# "above / more than / تزيد / أكتر / aktar" + "million / SAR / قيمة / سعر / malyon" = an amount threshold question.
# Arabic words are matched as word starts, so قيمتها and سعرها match too.
THRESHOLD_WORDS = re.compile(
    r"\b(above|over|more than|greater|exceed(s|ing)?|higher|below|under|less than|lower|aktar|a2al)\b|[<>]"
    r"|(^|\s)(اكثر|اكتر|تزيد|يزيد|تتجاوز|يتجاوز|اعلى|فوق|اقل|تقل|يقل|دون|تحت)"
)
AMOUNT_WORDS = re.compile(
    r"\b(million|thousand|billion|sar|riyals?|amounts?|costs?|prices?|values?|malyon|alf|se3r|as3ar)\b"
    r"|\b\d[\d,.]*\s*(k|m|mn|bn)\b|\d[\d,]{3,}"  # 5m, 1.5 mn, 1,000,000 - not "30 days"
    r"|(^|\s)(مليون|ملايين|الف|مليار|ريال|قيم|سعر|اسعار|مبلغ|مبالغ|تكلف|كلف)"
)
AMOUNT_NOTE = (
    "This asks for amounts above or below a value: answer it with query_table, called once without a "
    "document (it filters every table), on each row's total amount column (not a unit price or rate), with the "
    "value written in digits. "
    "Do not answer it from search_documents or read_document."
)


def asks_for_amount_threshold(*texts: str) -> bool:
    """True for "items above SAR 1 million" in English, Arabic, Lebanese or Arabizi."""
    text = normalize_arabic(" ".join(texts))
    return bool(THRESHOLD_WORDS.search(text) and AMOUNT_WORDS.search(text))


def question_with_notes(question: str, route: Route) -> str:
    """The user's question, then notes for the agent from the router."""
    notes = [STYLE_INSTRUCTIONS.get(route.style, STYLE_INSTRUCTIONS["en"])]
    notes.append("Never translate file names, numbers or item codes.")
    if route.intent == "follow_up":
        notes.append("This is about your previous answer in the chat: reuse its facts and sources if enough.")
    if route.question_en and route.question_en != question:
        notes.append(f"In English: {route.question_en}")
    if route.question_ar and route.question_ar != question:
        notes.append(f"In Arabic: {route.question_ar}")
    if route.intent != "follow_up" and asks_for_amount_threshold(question, route.question_en):
        notes.append(AMOUNT_NOTE)
    elif route.question_en and route.question_ar:
        notes.append("When you use search_documents, search with the English AND the Arabic version.")
    if route.search_terms:
        notes.append("Useful terms (also for table columns): " + ", ".join(route.search_terms))
    return question + "\n\n[Notes for you, not from the user]\n" + "\n".join(f"- {note}" for note in notes)
