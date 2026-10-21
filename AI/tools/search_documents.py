"""Tool: semantic (RAG) search over all document text and table rows."""

from AI.language.arabic_normalizer import normalize_arabic
from AI.rag.keywords import keywords
from AI.tools.lookup import find_document, means_all_documents
from AI.tools.tool_context import ToolContext, ToolError, ToolResult

DEFAULT_TOP_K = 6
MAX_TOP_K = 8
MAX_OTHER_FILES = 3
OTHER_TEXT_CHARS = 160


def other_files_with_words(context: ToolContext, query: str, searched: str) -> list[dict]:
    """Other files whose passages contain the query's words: a search kept to one file must not hide them
    (the lift count was in the Arabic appendix while every search stayed inside the English contract)."""
    words = [normalize_arabic(word) for word in keywords(query)]
    found: dict[str, dict] = {}
    for match in context.vector_store.search(query, document=None, top_k=MAX_TOP_K):
        text = normalize_arabic(match["text"].lower())
        if match["document"] != searched and match["document"] not in found and any(w in text for w in words):
            found[match["document"]] = {"document": match["document"], "location": match["location"],
                                        "text": match["text"][:OTHER_TEXT_CHARS]}  # fmt: skip
    return list(found.values())[:MAX_OTHER_FILES]


def search_documents(context: ToolContext, query: str, document: str | None = None, top_k: int = DEFAULT_TOP_K):
    """Best matching passages, each with file and page (or sheet rows)."""
    if context.vector_store is None:
        raise ToolError("Search is not available right now. Use read_document or query_table instead.")
    if not str(query or "").strip():
        raise ToolError("'query' cannot be empty.")
    name = None if means_all_documents(document) else find_document(context, document).name
    top_k = max(1, min(int(top_k or DEFAULT_TOP_K), MAX_TOP_K))
    matches = context.vector_store.search(str(query), document=name, top_k=top_k)
    data = {"query": query, "matches": matches}
    others = other_files_with_words(context, str(query), name) if name else []
    if others:
        data["also_in_other_files"] = others  # search these files too before saying something is not there
    where = f" in {name}" if name else ""
    also = f" (also found in {len(others)} other file{'s' if len(others) > 1 else ''})" if others else ""
    return ToolResult(data=data, step=f"Searched '{query}'{where}: {len(matches)} passages{also}")
