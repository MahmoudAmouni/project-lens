"""The note added under the user's question: which style to answer in, and the question in both languages."""

from AI.router import Route

STYLE_INSTRUCTIONS = {
    "en": "Reply in clear English.",
    "ar": "Reply in Modern Standard Arabic.",
    "ar-lb": "Reply in light, professional Lebanese Arabic written in Arabic letters "
    "(for example: في 14 بند أكتر من مليون ريال، أكبرهن...).",
    "arabizi": "Reply in Lebanese Arabic written in Latin letters (Arabizi), like the user writes "
    "(for example: Fi 14 items aktar men malyon SAR, akbar wehde...).",
}


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
    if route.question_en and route.question_ar:
        notes.append("When you use search_documents, search with the English AND the Arabic version.")
    if route.search_terms:
        notes.append("Useful terms (also for table columns): " + ", ".join(route.search_terms))
    return question + "\n\n[Notes for you, not from the user]\n" + "\n".join(f"- {note}" for note in notes)
