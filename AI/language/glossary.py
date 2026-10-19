"""Lebanese, Arabizi and project words: helps detect the user's style and widens keyword search."""

# Arabizi (Latin letters) -> (Lebanese in Arabic letters, English meaning)
ARABIZI = {
    "shu": ("شو", "what"), "chou": ("شو", "what"), "sho": ("شو", "what"),
    "baddi": ("بدي", "I want"), "badde": ("بدي", "I want"),
    "3tine": ("عطيني", "give me"), "a3tine": ("عطيني", "give me"),
    "aktar": ("أكتر", "more"), "a2al": ("أقل", "less"), "men": ("من", "than"),
    "malyon": ("مليون", "million"), "mawe3id": ("مواعيد", "dates"),
    "3a2ed": ("عقد", "contract"), "la5asli": ("لخصلي", "summarize for me"),
    "yalli": ("يلي", "that / which"), "kif": ("كيف", "how"), "kifak": ("كيفك", "how are you"),
    "ade": ("أديش", "how much"), "adesh": ("أديش", "how much"), "wen": ("وين", "where"),
    "emta": ("إيمتى", "when"), "bel": ("بال", "in the"), "fi": ("في", "there is / in"),
    "tene": ("التاني", "the second"), "kel": ("كل", "all"), "kellon": ("كلهن", "all of them"),
    "se3r": ("سعر", "price"), "as3ar": ("أسعار", "prices"), "ktebli": ("كتبلي", "write for me"),
}  # fmt: skip

# Only these carry meaning worth searching for; "shu", "yalli", "men"... are grammar.
ARABIZI_CONTENT_WORDS = {"malyon", "mawe3id", "3a2ed", "se3r", "as3ar"}

# Words that show Lebanese dialect written in Arabic letters.
LEBANESE_MARKERS = {"شو", "بدي", "يلي", "هيدا", "هيدي", "فيك", "عم", "كتير", "أكتر", "اكتر", "لخصلي", "عطيني",
                    "أديش", "اديش", "قديش", "وين", "هلق", "منيح", "ليش", "كيفك", "التاني", "تبع", "هيك", "كمان",
                    "شي", "بدك", "هيدول", "عنجد", "مش", "إيمتى", "ايمتى"}  # fmt: skip

# Project words in both languages, both ways.
PROJECT_TERMS = {
    "boq": "جدول الكميات", "bill of quantities": "جدول الكميات", "scope of work": "نطاق العمل",
    "deliverables": "المخرجات", "contractor": "المقاول", "employer": "صاحب العمل", "payment": "دفعة",
    "contract": "عقد", "amount": "المبلغ", "price": "السعر", "cost": "التكلفة", "total": "الإجمالي",
    "date": "تاريخ", "facade": "الواجهات", "retention": "المحتجزات", "penalty": "غرامة",
    "delay": "تأخير", "warranty": "ضمان", "specification": "المواصفات", "item": "بند",
}  # fmt: skip
ARABIC_TO_ENGLISH = {arabic: english for english, arabic in PROJECT_TERMS.items()}


def related_terms(text: str) -> list[str]:
    """Translations of project and Arabizi words found in the text (to search both languages)."""
    lowered = text.lower()
    found: list[str] = []
    for english, arabic in PROJECT_TERMS.items():
        if english in lowered:
            found.append(arabic)
        if arabic in text:
            found.append(english)
    for word in lowered.split():
        if word in ARABIZI_CONTENT_WORDS:
            found.append(ARABIZI[word][1])
    return list(dict.fromkeys(found))
