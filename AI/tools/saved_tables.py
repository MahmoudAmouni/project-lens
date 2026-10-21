"""Keep query_table rows so submit_answer can show them without the model retyping any number."""

from AI.tools.lookup import simplify
from AI.tools.tool_context import ToolContext

MAX_SAVED_TABLES = 20
SAME_MEANING = {"itemno": "Item", "itemnumber": "Item", "item": "Item", "qty": "Qty", "quantity": "Qty"}
HIDDEN_KEYS = {"row", "source", "Page", "Source page", "is_total"}  # the Source column already has file + row/page
TOTAL_MARK = "__is_total"  # kept on a merged row (never a column) until the saved table lists its total rows


def merged_number_label(results: list[dict], wanted: str | None) -> str | None:
    """One name for the filtered number column across tables, e.g. "Amount (SAR)"."""
    if not wanted or len(results) < 2:
        return None
    currencies = {r["sums"].get(r["amount_column"] or "", {}).get("currency") for r in results}
    label = str(wanted).strip().title()
    return f"{label} ({currencies.pop()})" if len(currencies) == 1 and None not in currencies else label


def merged_rows(results: list[dict], number_label: str | None) -> tuple[list[str], list[dict]]:
    columns: list[str] = []
    rows: list[dict] = []
    for result in results:
        for row in result["rows"]:
            merged = {}
            for key, value in row.items():
                if key in HIDDEN_KEYS:
                    continue
                if number_label and key == result["amount_column"]:
                    name = number_label
                else:
                    name = SAME_MEANING.get(simplify(key), key)
                merged[name] = value
                if name not in columns:
                    columns.append(name)
            merged["Source"] = row["source"]
            if row.get("is_total"):
                merged[TOTAL_MARK] = True
            rows.append(merged)
    return [*columns, "Source"], rows


def saved_table_ids(value: object) -> list[str]:
    """Accept "t1", "t1,t2" or ["t1", "t2"]."""
    items = value if isinstance(value, list) else str(value or "").split(",")
    return [str(item).strip() for item in items if str(item).strip()]


def combine_saved_tables(context: ToolContext, table_ids: list[str]) -> dict:
    """One table from several saved results (columns are merged by name)."""
    columns: list[str] = []
    rows: list[dict] = []
    total_rows: list[int] = []  # subtotal / grand total lines: the screen shows them but leaves them out of its total
    for table_id in table_ids:
        saved = context.saved_tables[table_id]
        total_rows += [len(rows) + index for index in saved.get("total_rows", [])]
        rows += [dict(zip(saved["columns"], row, strict=True)) for row in saved["rows"]]
        columns += [c for c in saved["columns"] if c not in columns]
    columns = [c for c in columns if c != "Source"] + ["Source"]
    table = {"columns": columns, "rows": [[row.get(c) for c in columns] for row in rows]}
    return {**table, "total_rows": total_rows} if total_rows else table


def save_table(context: ToolContext, results: list[dict], wanted_number_column: str | None) -> str | None:
    """Save the matching rows of all tables as one table; returns its id (e.g. "t3"), or None if empty."""
    columns, rows = merged_rows(results, merged_number_label(results, wanted_number_column))
    if not rows:
        return None
    table_id = f"t{len(context.saved_tables) + 1}"
    context.saved_tables[table_id] = {
        "columns": columns,
        "rows": [[row.get(c) for c in columns] for row in rows],
        "total_rows": [index for index, row in enumerate(rows) if row.get(TOTAL_MARK)],
    }
    for old_id in list(context.saved_tables)[:-MAX_SAVED_TABLES]:
        del context.saved_tables[old_id]
    return table_id
