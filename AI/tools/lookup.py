"""Find documents, tables and columns by loose names: "boq phase1" finds "BOQ_Phase1.xlsx"."""

import difflib
import re

from AI.tools.tool_context import DocumentLike, TableLike, ToolContext, ToolError


def simplify(name: str) -> str:
    """Lower case letters and digits only: "Total Amount (SAR)" -> "totalamountsar"."""
    return re.sub(r"[\W_]+", "", name.lower())


def best_match(wanted: str, names: list[str]) -> str | None:
    """Exact, then simplified, then "contains", then close spelling."""
    if wanted in names:
        return wanted
    simple_wanted = simplify(wanted)
    simple = {simplify(name): name for name in names}
    if simple_wanted in simple:
        return simple[simple_wanted]
    stem_matches = [name for name in names if simplify(name.rsplit(".", 1)[0]) == simple_wanted]
    if stem_matches:
        return stem_matches[0]
    containing = [name for name in names if simple_wanted and simple_wanted in simplify(name)]
    if containing:
        return min(containing, key=len)
    close = difflib.get_close_matches(simple_wanted, list(simple), n=1, cutoff=0.75)
    return simple[close[0]] if close else None


ALL_DOCUMENT_WORDS = {"", "*", "all", "none", "null"}  # open models sometimes send "None" as text


def means_all_documents(name: object) -> bool:
    """True when the model means every document (left out, "*", or "None"/"null" written as text)."""
    return name is None or str(name).strip().lower() in ALL_DOCUMENT_WORDS


def find_document(context: ToolContext, name: str) -> DocumentLike:
    """The document with this (loose) name, or a ToolError listing the real names."""
    names = [document.name for document in context.documents]
    match = best_match(str(name), names)
    if match is None:
        raise ToolError(f"No document named '{name}'. Documents: {', '.join(names)}")
    document = next(d for d in context.documents if d.name == match)
    if document.status != "ok":
        raise ToolError(f"'{document.name}' cannot be read: {document.status}. {document.message}")
    return document


def find_table(document: DocumentLike, table_id: str | None) -> TableLike:
    """The table with this id. With no id, the only table of the document."""
    if not document.tables:
        raise ToolError(f"'{document.name}' has no tables.")
    ids = [table.id for table in document.tables]
    if not table_id:
        if len(ids) == 1:
            return document.tables[0]
        raise ToolError(f"'{document.name}' has several tables; choose a table_id from: {', '.join(ids)}")
    match = best_match(str(table_id), ids)
    if match is None:
        raise ToolError(f"No table '{table_id}' in '{document.name}'. Tables: {', '.join(ids)}")
    return next(table for table in document.tables if table.id == match)


def find_column(table: TableLike, wanted: str) -> str | None:
    """The real column name for a loose name ("amount" -> "Total Amount (SAR)"), or None."""
    columns = [str(column) for column in table.data.columns]
    match = best_match(str(wanted), columns)
    if match is not None:
        return match
    words = [word for word in re.split(r"\W+", str(wanted).lower()) if word]
    scored = [(sum(word in column.lower() for word in words), column) for column in columns]
    best_score, best_column = max(scored, default=(0, None))
    return best_column if best_score else None


def require_column(table: TableLike, wanted: str) -> str:
    """Like find_column, but a ToolError with the real column names when nothing fits."""
    column = find_column(table, wanted)
    if column is None:
        columns = ", ".join(str(c) for c in table.data.columns)
        raise ToolError(f"No column like '{wanted}' in table '{table.id}'. Columns: {columns}")
    return column
