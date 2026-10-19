"""Tool: semantic (RAG) search over all document text and table rows."""

from AI.tools.lookup import find_document, means_all_documents
from AI.tools.tool_context import ToolContext, ToolError, ToolResult

DEFAULT_TOP_K = 6
MAX_TOP_K = 8


def search_documents(context: ToolContext, query: str, document: str | None = None, top_k: int = DEFAULT_TOP_K):
    """Best matching passages, each with file and page (or sheet rows)."""
    if context.vector_store is None:
        raise ToolError("Search is not available right now. Use read_document or query_table instead.")
    if not str(query or "").strip():
        raise ToolError("'query' cannot be empty.")
    name = None if means_all_documents(document) else find_document(context, document).name
    top_k = max(1, min(int(top_k or DEFAULT_TOP_K), MAX_TOP_K))
    matches = context.vector_store.search(str(query), document=name, top_k=top_k)
    where = f" in {name}" if name else ""
    return ToolResult(
        data={"query": query, "matches": matches},
        step=f"Searched '{query}'{where}: {len(matches)} passages",
    )
