"""A second look before refusing: a question that uses the documents' own words is never called off-topic.

Small router models sometimes call a real question off-topic ("shu l items bel civil BOQ yalli aktar men malyon?").
The words of the loaded files (file, table and column names) and the project glossary decide instead.
One shared word is not enough ("a poem about concrete"), so off-topic questions still get the polite refusal.
"""

import re

from AI.language.arabic_normalizer import normalize_arabic
from AI.language.glossary import ARABIZI_CONTENT_WORDS, PROJECT_TERMS, SYNONYM_GROUPS
from AI.rag.keywords import NORMALIZED_STOP_WORDS

MIN_SHARED_WORDS = 2
MIN_WORD_LENGTH = 3
ARABIC_PREFIX = re.compile("^(وال|بال|كال|فال|لل|ال)(?=...)")  # "the", "and the", "for the"... in front of a word
GLOSSARY_TEXTS = [
    *PROJECT_TERMS,
    *PROJECT_TERMS.values(),
    *ARABIZI_CONTENT_WORDS,
    *(word for group in SYNONYM_GROUPS for word in group),
]


def words_of(text: str) -> set[str]:
    """Letters-only words, lower case, Arabic normalized: "BOQ_Civil_Works" -> {"boq", "civil", "works"}."""
    found = (ARABIC_PREFIX.sub("", normalize_arabic(word)) for word in re.findall(r"[^\W\d_]+", str(text).lower()))
    return {word for word in found if len(word) >= MIN_WORD_LENGTH and word not in NORMALIZED_STOP_WORDS}


def document_words(documents) -> set[str]:
    """The words a question about these files is likely to use: names of files, tables and columns, and the glossary."""
    names = []
    for document in documents:
        names.append(document.name.rsplit(".", 1)[0])
        for table in document.tables:
            names.append(table.id)
            names.extend(str(column) for column in table.data.columns)
    return words_of(" ".join(names + GLOSSARY_TEXTS))


def mentions_documents(question: str, vocabulary: set[str]) -> bool:
    """True when the question shares at least two words with the documents' vocabulary."""
    return len(words_of(question) & vocabulary) >= MIN_SHARED_WORDS
