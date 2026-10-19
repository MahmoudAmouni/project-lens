"""Fixed replies (not written by the model): greeting, out of scope and not found, one per writing style,
plus example questions that match the loaded files. Fixed texts are always short, polite and correct."""

GREETING = {
    "en": "Hello! I answer questions about the loaded project documents, with the file and page for every answer. "
    "You could ask:",
    "ar": "مرحباً! أجيب عن الأسئلة المتعلقة بالمستندات المحمّلة، مع ذكر الملف والصفحة لكل إجابة. يمكنك أن تسأل:",
    "ar-lb": "أهلا! أنا بجاوب عن الملفات يلي حمّلتها، ومع كل جواب بقلّك الملف والصفحة. فيك تسألني مثلاً:",
    "arabizi": "Ahla! Ana bjeweb 3an l files yalli 7ammaltun, w ma3 kel jaweb b2ellak l file wel page. "
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
    """The text for a greeting, out_of_scope or not_found reply."""
    texts = {"greeting": GREETING, "out_of_scope": OUT_OF_SCOPE, "not_found": NOT_FOUND}[kind]
    return texts.get(style, texts["en"])
