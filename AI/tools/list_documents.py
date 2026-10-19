"""Tool: list every loaded file with its status, pages and tables."""

from AI.tools.tool_context import ToolContext, ToolResult


def describe_tables(document) -> list[dict]:
    return [
        {
            "table_id": table.id,
            "location": table.location,
            "rows": len(table.data),
            "columns": [str(column) for column in table.data.columns],
            "currencies": table.currencies,
        }
        for table in document.tables
    ]


MAX_OVERVIEW_CHARS = 2_500


def document_overview(documents) -> str:
    """A short list of the files for the system prompt, so most questions skip the list_documents round."""
    lines = []
    for document in documents:
        if document.status != "ok":
            lines.append(f"- {document.name}: cannot be read ({document.status})")
            continue
        parts = [f"{len(document.pages)} pages"] if document.pages else []
        for table in document.tables:
            columns = ", ".join(str(column) for column in table.data.columns)
            parts.append(f"table '{table.id}' ({len(table.data)} rows: {columns})")
        lines.append(f"- {document.name}: " + "; ".join(parts))
    overview = "\n".join(lines)
    if len(overview) > MAX_OVERVIEW_CHARS:
        overview = overview[:MAX_OVERVIEW_CHARS] + "\n... (more files: call list_documents)"
    return overview


def list_documents(context: ToolContext) -> ToolResult:
    """Every file: name, type, status, page count, tables with rows and columns."""
    documents = []
    for document in context.documents:
        entry = {"name": document.name, "type": document.file_type, "status": document.status}
        if document.message:
            entry["note"] = document.message
        if document.pages:
            entry["pages"] = len(document.pages)
        if document.tables:
            entry["tables"] = describe_tables(document)
        documents.append(entry)
    readable = sum(document.status == "ok" for document in context.documents)
    return ToolResult(
        data={"documents": documents, "readable": readable, "not_readable": len(documents) - readable},
        step=f"Listed {len(documents)} documents ({readable} readable)",
    )
