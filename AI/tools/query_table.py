"""Tool: exact filtering of tables (e.g. amount > 1,000,000). Checks every row; returns rows, count and sums."""

import re

import pandas as pd

from AI.tools.lookup import find_document, find_table, means_all_documents, require_column
from AI.tools.saved_tables import save_table
from AI.tools.table_filters import apply_filters, filter_columns
from AI.tools.tool_context import ToolContext, ToolError, ToolResult, to_plain

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
ROWS_FOR_MODEL = 8  # per table; all rows go to the saved table (Groq free tier limits)
ALL_DOCUMENTS = "*"
NOT_AN_AMOUNT = re.compile(r"\b(rate|unit|qty|quantity|page|no\.?|number)\b|%", re.I)  # not money columns
AMOUNT_NAME = re.compile(r"amount|total|cost|value|price|sum|المبلغ|القيمة|الإجمالي", re.I)
SUMMARY_SHEET = re.compile(r"summary|recap|totals?\b|ملخص|الإجمالي", re.I)  # repeat other sheets' totals


def row_source(document, table, row_number: int, row: pd.Series) -> str:
    """Citation for one row: "BOQ.xlsx · BOQ · row 47" or "BOQ.pdf · p. 3"."""
    if document.file_type == "pdf" and "Page" in row.index:
        return f"{document.name} · p. {to_plain(row['Page'])}"
    return f"{document.name} · {table.id} · row {row_number}"


def numeric_sums(table, rows: pd.DataFrame) -> dict:
    """Sum of every number column over the matching rows, with its currency when known."""
    sums = {}
    for column in rows.columns:
        if pd.api.types.is_numeric_dtype(rows[column]) and str(column) not in ("Page", "Source page"):
            sums[str(column)] = {"sum": to_plain(rows[column].sum()), "currency": table.currencies.get(column)}
    return sums


def main_amount_column(table, data: pd.DataFrame) -> str | None:
    """The column that holds each row's amount: a money column, not a rate or quantity; the largest sum wins."""
    candidates = [
        column
        for column in data.columns
        if pd.api.types.is_numeric_dtype(data[column]) and not NOT_AN_AMOUNT.search(str(column))
    ]
    with_currency = [column for column in candidates if column in table.currencies]
    named = [column for column in candidates if AMOUNT_NAME.search(str(column))]
    pool = with_currency or named
    return str(max(pool, key=lambda column: abs(data[column].sum()))) if pool else None


def query_one_table(document, table, filters, columns, sort_by, descending, limit, include_total_rows) -> dict:
    data = table.data
    if not include_total_rows and table.summary_rows:
        data = data.drop(index=[r for r in table.summary_rows if r in data.index])
    mask, notes, number_column = apply_filters(table, filters)
    amount_column = number_column or main_amount_column(table, data)
    matches = data[mask.reindex(data.index, fill_value=False)]

    if sort_by:
        sort_column = require_column(table, sort_by)
        matches = matches.sort_values(sort_column, ascending=not descending, na_position="last")
    shown_columns = [require_column(table, c) for c in columns] if columns else list(matches.columns)

    rows = []
    for row_number, row in matches.head(limit).iterrows():
        values = {str(c): to_plain(row[c]) for c in shown_columns}
        rows.append({"row": int(row_number), **values, "source": row_source(document, table, row_number, row)})
    result = {
        "document": document.name,
        "table_id": table.id,
        "location": table.location,
        "match_count": int(len(matches)),
        "amount_column": amount_column,
        "sums": numeric_sums(table, matches),
        "rows": rows,
    }
    if len(matches) > limit:
        result["not_shown"] = f"{len(matches) - limit} more rows match; count and sums include them."
    if notes:
        result["notes"] = notes
    return result


def tables_to_search(
    context: ToolContext, document: str, table_id: str | None, filters: list[dict]
) -> tuple[list, list[str]]:
    """(document, table) pairs to query, and the summary sheets left out.

    One table normally; with document "*", every table that has the filter columns, except summary
    sheets, which repeat totals from other sheets and would count them twice.
    """
    if not means_all_documents(document):
        found = find_document(context, document)
        return [(found, find_table(found, table_id))], []
    pairs, left_out = matching_tables(context, filters)
    if not pairs:
        raise ToolError("No table has all the filter columns. Use describe_table to check column names.")
    return pairs, left_out


def matching_tables(context: ToolContext, filters: list[dict]) -> tuple[list, list[str]]:
    """Every (document, table) with the filter columns, and the summary sheets among them (left out)."""
    pairs, left_out = [], []
    for doc in context.documents:
        for table in doc.tables if doc.status == "ok" else []:
            if not filter_columns(table, filters):
                continue
            if SUMMARY_SHEET.search(table.id):
                left_out.append(f"{doc.name} · {table.id}")
            else:
                pairs.append((doc, table))
    return pairs, left_out


def other_matching_tables(context: ToolContext, searched: list, filters: list[dict]) -> list[str]:
    """Tables NOT searched that also have the filter columns, so the model does not miss other BOQs."""
    if not filters:
        return []
    searched_ids = {(doc.name, table.id) for doc, table in searched}
    pairs, _ = matching_tables(context, filters)
    return [f"{doc.name} · {table.id}" for doc, table in pairs if (doc.name, table.id) not in searched_ids]


def combined_sums(results: list[dict]) -> dict:
    """Grand total of each table's amount column, per currency (never mixing currencies)."""
    totals: dict[str, float] = {}
    for result in results:
        column = result["amount_column"]
        if column and column in result["sums"]:
            currency = result["sums"][column]["currency"] or "unknown currency"
            totals[currency] = to_plain(totals.get(currency, 0) + (result["sums"][column]["sum"] or 0))
    return totals


def first_number_filter_column(filters: list[dict] | None) -> str | None:
    for item in filters or []:
        if isinstance(item, dict) and str(item.get("operator", "")).strip() in (">", ">=", "<", "<="):
            return item.get("column")
    return None


def query_table(
    context: ToolContext,
    document: str = ALL_DOCUMENTS,
    table_id: str | None = None,
    filters: list[dict] | None = None,
    columns: list[str] | None = None,
    sort_by: str | None = None,
    descending: bool = True,
    limit: int = DEFAULT_LIMIT,
    include_total_rows: bool = False,
) -> ToolResult:
    """Rows matching all filters, with their source row, plus the full match count and sums."""
    limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))
    results = []
    pairs, left_out = tables_to_search(context, document, table_id, filters or [])
    for found, table in pairs:
        try:
            results.append(
                query_one_table(found, table, filters, columns, sort_by, descending, limit, include_total_rows)
            )
        except ToolError:
            if not means_all_documents(document):
                raise
    total = sum(result["match_count"] for result in results)
    data: dict = {"total_match_count": total, "tables": results}
    if len(results) > 1:
        data["combined_sum_by_currency"] = combined_sums(results)
    if left_out:
        data["summary_sheets_left_out"] = left_out
    others = other_matching_tables(context, pairs, filters or [])
    if others:
        data["other_tables_with_these_columns"] = others
        data["note"] = (
            f"Only one table was searched; {len(others)} other tables have these columns. If the question is "
            "about all files, call query_table again WITHOUT document to search every table at once."
        )
    saved_id = save_table(context, results, first_number_filter_column(filters) or "Amount")
    if saved_id:
        data["table_result_id"] = saved_id
        data["how_to_show_rows"] = f"Pass table_result_id='{saved_id}' to submit_answer; do not retype the rows."
    for result in results:
        if len(result["rows"]) > ROWS_FOR_MODEL:
            result["rows_not_shown_here"] = len(result["rows"]) - ROWS_FOR_MODEL
            result["rows"] = result["rows"][:ROWS_FOR_MODEL]
    names = ", ".join(f"{r['document']} · {r['table_id']}" for r in results)
    return ToolResult(data=data, step=f"Filtered {names}: {total} rows")
