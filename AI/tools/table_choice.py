"""Which tables one query_table call searches: one table, every sheet of one file, or every table of every file."""

import re

from AI.tools.lookup import find_document, find_table, means_all_documents
from AI.tools.table_filters import filter_columns
from AI.tools.tool_context import ToolContext, ToolError

SUMMARY_SHEET = re.compile(r"summary|recap|totals?\b|ملخص|الإجمالي", re.I)  # repeat other sheets' totals


def usable_tables(document, filters: list[dict]) -> tuple[list, list[str]]:
    """(document, table) pairs of one file that have the filter columns, and its summary sheets (left out)."""
    pairs, left_out = [], []
    for table in document.tables if document.status == "ok" else []:
        if not filter_columns(table, filters):
            continue
        if SUMMARY_SHEET.search(table.id):
            left_out.append(f"{document.name} · {table.id}")
        else:
            pairs.append((document, table))
    return pairs, left_out


def matching_tables(context: ToolContext, filters: list[dict]) -> tuple[list, list[str]]:
    """Every (document, table) with the filter columns, and the summary sheets among them (left out)."""
    pairs, left_out = [], []
    for document in context.documents:
        found, skipped = usable_tables(document, filters)
        pairs += found
        left_out += skipped
    return pairs, left_out


def tables_to_search(
    context: ToolContext, document: str, table_id: str | None, filters: list[dict]
) -> tuple[list, list[str]]:
    """(document, table) pairs to query, and the summary sheets left out.

    A table_id gives that one table. A file without a table_id gives every sheet of that file, and no file
    gives every table of every file; summary sheets are left out there, as they repeat other sheets' totals.
    """
    if not means_all_documents(document):
        found = find_document(context, document)
        if table_id or len(found.tables) <= 1:
            return [(found, find_table(found, table_id))], []
        pairs, left_out = usable_tables(found, filters)
        if not pairs:  # only a summary sheet has these columns: then it is the one asked about
            pairs, left_out = [(found, table) for table in found.tables if filter_columns(table, filters)], []
        if not pairs:
            names = ", ".join(table.id for table in found.tables)
            raise ToolError(f"No table in '{found.name}' has all the filter columns. Tables: {names}")
        return pairs, left_out
    pairs, left_out = matching_tables(context, filters)
    if not pairs:
        raise ToolError("No table has all the filter columns. Use describe_table to check column names.")
    return pairs, left_out


def other_matching_tables(context: ToolContext, searched: list, filters: list[dict]) -> list[str]:
    """Tables NOT searched that also have the filter columns, so the model does not miss other BOQs."""
    if not filters:
        return []
    searched_ids = {(doc.name, table.id) for doc, table in searched}
    pairs, _ = matching_tables(context, filters)
    return [f"{doc.name} · {table.id}" for doc, table in pairs if (doc.name, table.id) not in searched_ids]
