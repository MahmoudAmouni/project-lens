"""Tool: exact filtering of tables (e.g. amount > 1,000,000). Checks every row; returns rows, count and sums."""

import re

import pandas as pd

from AI.tools.filter_shapes import normal_columns, normal_filters, normal_flag
from AI.tools.lookup import require_column
from AI.tools.saved_tables import save_table
from AI.tools.table_choice import other_matching_tables, tables_to_search
from AI.tools.table_filters import apply_filters
from AI.tools.table_ranking import keep_overall_best, rank_across_tables
from AI.tools.tool_context import ToolContext, ToolError, ToolResult, to_plain

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
ROWS_FOR_MODEL = 8  # per table for Groq (small free tier); big-limit models see more (context.rows_for_model)
BIG_ROWS_FOR_MODEL = 60  # Gemini / OpenRouter: the model sees the rows instead of guessing the hidden ones
ALL_DOCUMENTS = "*"
NOT_AN_AMOUNT = re.compile(r"\b(rate|unit|qty|quantity|page|no\.?|number)\b|%", re.I)  # not money columns
AMOUNT_NAME = re.compile(r"amount|total|cost|value|price|sum|المبلغ|القيمة|الإجمالي", re.I)


def row_source(document, table, row_number: int, row: pd.Series) -> str:
    """Citation for one row: "BOQ.xlsx · BOQ · row 47" or "BOQ.pdf · p. 3"."""
    if document.file_type in ("pdf", "word") and "Page" in row.index:
        return f"{document.name} · p. {to_plain(row['Page'])}"
    return f"{document.name} · {table.id} · row {row_number}"


def numeric_sums(table, rows: pd.DataFrame) -> dict:
    """Sum of every number column over the matching rows, with its currency when known.
    Total and subtotal lines are never added: they already hold the sum of the items (counting them doubles it)."""
    rows = rows.drop(index=[number for number in table.summary_rows if number in rows.index])
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
        if row_number in table.summary_rows:
            rows[-1]["is_total"] = True  # a subtotal or grand total line: shown, but never added up again
    result = {
        "document": document.name,
        "table_id": table.id,
        "location": table.location,
        "match_count": int(len(matches)),
        "amount_column": amount_column,
        "sums": numeric_sums(table, matches),
        "rows": rows,
    }
    if sort_by:
        result["sort_column"] = str(sort_column)
    if len(matches) > limit:
        result["not_shown"] = f"{len(matches) - limit} more rows match; count and sums include them."
    if notes:
        result["notes"] = notes
    total_lines = sum(1 for row in rows if row.get("is_total"))
    if total_lines:
        result["total_lines"] = f"{total_lines} row(s) marked is_total are the file's own totals; sums leave them out."
    return result


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
    filters, columns = normal_filters(filters), normal_columns(columns)  # models write these in many shapes
    descending, include_total_rows = normal_flag(descending, True), normal_flag(include_total_rows, False)
    limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))
    results, errors = [], []
    pairs, left_out = tables_to_search(context, document, table_id, filters or [])
    for found, table in pairs:
        try:
            results.append(
                query_one_table(found, table, filters, columns, sort_by, descending, limit, include_total_rows)
            )
        except ToolError as error:
            if len(pairs) == 1:
                raise
            errors.append(error)
    if errors and not results:
        raise errors[0]  # e.g. a sort_by column no table has: say so, never a silent "0 rows"
    if sort_by and len(results) > 1:  # "the most expensive item": the best rows of every table together
        keep_overall_best(results, rank_across_tables(results, descending, limit))
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
            f"Only part of the files was searched; {len(others)} other tables have these columns. If the question "
            "is about all files, call query_table again WITHOUT document to search every table at once."
        )
    saved_id = save_table(context, results, first_number_filter_column(filters) or "Amount")
    if saved_id:
        data["table_result_id"] = saved_id
        data["how_to_show_rows"] = f"Pass table_result_id='{saved_id}' to submit_answer; do not retype the rows."
    if sort_by and len(results) > 1:
        data["best_rows_of_all_tables"] = rank_across_tables(results, descending, context.rows_for_model)
    for result in results:
        if len(result["rows"]) > context.rows_for_model:
            result["rows_not_shown_here"] = len(result["rows"]) - context.rows_for_model
            result["rows"] = result["rows"][: context.rows_for_model]
    names = ", ".join(f"{r['document']} · {r['table_id']}" for r in results)
    return ToolResult(data=data, step=f"Filtered {names}: {total} rows")
