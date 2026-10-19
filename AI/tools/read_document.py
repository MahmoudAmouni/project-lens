"""Tool: read the text of a range of PDF pages, in order."""

from AI.tools.lookup import find_document
from AI.tools.tool_context import ToolContext, ToolError, ToolResult

MAX_PAGES_PER_CALL = 10
MAX_TEXT_CHARS = 5_000


def read_document(context: ToolContext, document: str, start_page: int = 1, end_page: int | None = None) -> ToolResult:
    """Text of pages start_page..end_page (1-based, max 10 pages). Says if more pages exist."""
    found = find_document(context, document)
    if not found.pages:
        raise ToolError(f"'{found.name}' has no text pages (it is a spreadsheet). Use describe_table and query_table.")

    total = len(found.pages)
    start = max(1, int(start_page or 1))
    if start > total:
        raise ToolError(f"'{found.name}' has only {total} pages.")
    end = min(total, int(end_page or start + MAX_PAGES_PER_CALL - 1), start + MAX_PAGES_PER_CALL - 1)

    pages, used_chars = [], 0
    for page in found.pages[start - 1 : end]:
        if pages and used_chars + len(page.text) > MAX_TEXT_CHARS:
            break
        text = page.text[: MAX_TEXT_CHARS - used_chars]
        pages.append({"page": page.number, "text": text})
        used_chars += len(text)
    last_read = pages[-1]["page"]

    data = {"document": found.name, "total_pages": total, "pages": pages}
    if last_read < total:
        data["more"] = f"Pages {last_read + 1}-{total} not read yet. Call again with start_page={last_read + 1}."
    label = f"page {start}" if start == last_read else f"pages {start}-{last_read}"
    return ToolResult(data=data, step=f"Read {found.name} {label}")
