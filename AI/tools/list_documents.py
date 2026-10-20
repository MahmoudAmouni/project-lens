"""Tool: list every loaded file with its status, pages and tables."""

import pandas as pd

from AI.tools.query_table import AMOUNT_NAME
from AI.tools.tool_context import ToolContext, ToolResult

NOT_STATED = "currency not stated"


def currency_text(table) -> str | None:
    """'USD' / 'SAR, USD' for the table's money columns, 'currency not stated' when it has money columns
    without one (the model must not assume SAR), or None when the table holds no money."""
    if table.currencies:
        return ", ".join(sorted(set(table.currencies.values())))
    data = table.data
    money = [c for c in data.columns if AMOUNT_NAME.search(str(c)) and pd.api.types.is_numeric_dtype(data[c])]
    return NOT_STATED if money else None


def describe_tables(document) -> list[dict]:
    return [
        {
            "table_id": table.id,
            "location": table.location,
            "rows": len(table.data),
            "columns": [str(column) for column in table.data.columns],
            "currencies": table.currencies or currency_text(table),
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
            currency = currency_text(table)
            parts.append(f"table '{table.id}' ({len(table.data)} rows: {columns}{'; ' + currency if currency else ''})")
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
