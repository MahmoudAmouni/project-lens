"""What the tools found, in a few lines, for the last forced answer.

After many rounds the model tends to answer from its latest (often empty) searches and forget a fact it found in
round one ("Retention of 5%"). This digest picks the lines of ALL tool results that mention the question's
keywords, oldest first, so the final answer still sees them. Only text the tools returned is used.
"""

import re

from AI.rag.keywords import keywords

PIECE = re.compile(r'(?<=[.!?])\s+|\\n|\n|,\s*(?="[\w ]+"\s*:)|\},\s*\{')  # sentences, lines and JSON fields
JSON_KEY = re.compile(r'^[\w ]+"\s*:\s*[\[{]*\s*(?:"[\w ]+"\s*:\s*)?"?')  # 'text": "' left over from the JSON
MAX_LINES = 12
MAX_LINE_CHARS = 300
MIN_LINE_CHARS = 12


def findings_digest(question: str, tool_texts: list[str]) -> str:
    """'- line' for each tool-result line with a question keyword (no repeats); "" when nothing matches."""
    words = [word for word in keywords(question.split("\n\n[Notes", 1)[0]) if len(word) >= 3]
    if not words:
        return ""
    found: list[str] = []
    for text in tool_texts:
        for piece in PIECE.split(str(text)):
            line = JSON_KEY.sub("", piece.strip(' "{}[]')).strip(' "{}[]')
            lowered = line.lower()
            if len(line) >= MIN_LINE_CHARS and any(word in lowered for word in words) and line not in found:
                found.append(line[:MAX_LINE_CHARS])
                if len(found) == MAX_LINES:
                    return "\n".join(f"- {line}" for line in found)
    return "\n".join(f"- {line}" for line in found)
