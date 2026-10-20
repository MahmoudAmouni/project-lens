"""Fixed replies (not written by the model): greeting, out of scope and not found, one per writing style,
plus example questions that match the loaded files. Fixed texts are always short, polite and correct."""

GREETING = {
    "en": "Hello! I'm ProjectLens. I answer questions about the loaded project documents, "
    "with the file and page for every answer. You could ask:",
    "ar": "مرحباً! أنا بصيرة. أجيب عن الأسئلة المتعلقة بالمستندات المحمّلة، "
    "مع ذكر الملف والصفحة لكل إجابة. يمكنك أن تسأل:",
    "ar-lb": "أهلا! أنا بصيرة، بجاوب عن الملفات يلي حمّلتها، ومع كل جواب بقلّك الملف والصفحة. فيك تسألني مثلاً:",
    "arabizi": "Ahla! Ana ProjectLens, bjeweb 3an l files yalli 7ammaltun, w ma3 kel jaweb b2ellak l file wel page. "
    "Fik tes2alne masalan:",
}

OUT_OF_SCOPE = {
    "en": "Sorry, I can only answer questions about the loaded documents. You could ask:",
    "ar": "عذراً، يمكنني الإجابة فقط عن الأسئلة المتعلقة بالمستندات المحمّلة. يمكنك أن تسأل:",
    "ar-lb": "عفواً، أنا بس بجاوب عن الملفات يلي حمّلتها. فيك تسألني مثلاً:",
    "arabizi": "Sorry, ana bas bjeweb 3an l files yalli 7ammaltun. Fik tes2alne masalan:",
}

NOT_FOUND = {
    "en": "I couldn't find this in the loaded documents.",
    "ar": "لم أجد هذه المعلومة في المستندات المحمّلة.",
    "ar-lb": "ما لقيت هالمعلومة بالملفات يلي حمّلتها.",
    "arabizi": "Ma la2et hal ma3lume bel files yalli 7ammaltun.",
}

TABLE_ONLY = {  # the model's text had numbers no tool returned, so only the exact rows are shown
    "en": "Here are the matching rows, exactly as they appear in the files:",
    "ar": "هذه هي الصفوف المطابقة، كما وردت في الملفات تماماً:",
    "ar-lb": "هيدي الصفوف يلي بتطابق، متل ما هيي بالملفات:",
    "arabizi": "Hayde l rows yalli btetaba2, metel ma hiye bel files:",
}

CLARIFY = {  # "?", "." or one letter: nothing to answer yet
    "en": "Could you write your question in a few words? For example:",
    "ar": "هل يمكنك كتابة سؤالك ببضع كلمات؟ مثلاً:",
    "ar-lb": "فيك تكتبلي سؤالك بكم كلمة؟ مثلاً:",
    "arabizi": "Fik tektebli so2alak b kam kelme? Masalan:",
}

# (needs tables, question) per style: the cost question only when tables are loaded, the others need text.
EXAMPLES = {
    "en": [(True, "List all cost items above SAR 1 million"), (False, "Summarize the scope of work"),
           (False, "Extract all dates and deliverables")],
    "ar": [(True, "اذكر جميع البنود التي تزيد قيمتها عن مليون ريال"), (False, "لخّص نطاق العمل"),
           (False, "استخرج جميع التواريخ والمخرجات")],
    "ar-lb": [(True, "شو البنود يلي سعرها أكتر من مليون؟"), (False, "لخصلي نطاق العمل"),
              (False, "شو المواعيد والمخرجات بالعقد؟")],
    "arabizi": [(True, "shu l items yalli aktar men malyon?"), (False, "la5asli l scope of work"),
                (False, "shu l mawe3id wel deliverables bel 3a2ed?")],
}  # fmt: skip


def example_questions(documents, style: str) -> list[str]:
    """Up to 3 example questions in the user's style that the loaded files can answer."""
    readable = [document for document in documents if document.status == "ok"]
    has_tables = any(document.tables for document in readable)
    has_text = any(document.pages for document in readable)
    return [question for needs_tables, question in EXAMPLES.get(style, EXAMPLES["en"])
            if (has_tables if needs_tables else has_text)]  # fmt: skip


def fixed_reply(kind: str, style: str) -> str:
    """The text for a greeting, out_of_scope, clarify, not_found or table_only reply."""
    texts = {
        "greeting": GREETING, "out_of_scope": OUT_OF_SCOPE, "clarify": CLARIFY, "not_found": NOT_FOUND,
        "table_only": TABLE_ONLY,
    }[kind]  # fmt: skip
    return texts.get(style, texts["en"])
