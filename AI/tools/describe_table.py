"""Tool: column names, types and the first rows of one table."""

import pandas as pd

from AI.tools.lookup import find_document, find_table
from AI.tools.tool_context import ToolContext, ToolResult, to_plain

PREVIEW_ROWS = 5


def describe_column(table, column: str) -> dict:
    """Type, filled count, min/max and currency. Total rows are left out, like in query_table."""
    values = table.data[column].drop(index=table.summary_rows, errors="ignore")
    info = {"name": column, "type": "number" if pd.api.types.is_numeric_dtype(values) else "text"}
    info["filled"] = int(values.notna().sum())
    if info["type"] == "number" and info["filled"]:
        info["min"], info["max"] = to_plain(values.min()), to_plain(values.max())
    if column in table.currencies:
        info["currency"] = table.currencies[column]
    return info


def preview_rows(table) -> list[dict]:
    rows = []
    for row_number, row in table.data.head(PREVIEW_ROWS).iterrows():
        rows.append({"row": int(row_number), **{str(k): to_plain(v) for k, v in row.items()}})
    return rows


def describe_table(context: ToolContext, document: str, table_id: str | None = None) -> ToolResult:
    """Columns with types, row count, total rows and the first 5 rows."""
    found = find_document(context, document)
    table = find_table(found, table_id)
    data = {
        "document": found.name,
        "table_id": table.id,
        "location": table.location,
        "row_count": len(table.data),
        "columns": [describe_column(table, str(column)) for column in table.data.columns],
        "first_rows": preview_rows(table),
    }
    if getattr(table, "notes", None):
        data["title_lines"] = table.notes  # e.g. "Revision A (SUPERSEDED)": tells which version this is
    if table.summary_rows:
        data["total_rows"] = f"Rows {table.summary_rows} are Total/Subtotal rows; query_table leaves them out."
    return ToolResult(data=data, step=f"Described {found.name} · {table.id} ({len(table.data)} rows)")
