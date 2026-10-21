"""Tool: the final, structured answer. Calling it ends the agent loop."""

import re

from AI.tools.lookup import best_match
from AI.tools.saved_tables import combine_saved_tables, saved_table_ids
from AI.tools.tool_context import FinalAnswer, Source, ToolContext, ToolError, ToolResult, to_plain

# "1,450,000" or "1450000" become numbers so the table can sort and align them; item codes like "3.2" stay text.
NUMBER_TEXT = re.compile(r"-?(\d{1,3}(,\d{3})+|\d{5,})(\.\d+)?")
# The chat history marks earlier answers with "[Sources: ...]" and "[Table: ...]"; models copy them. The screen
# shows sources and tables itself, so these tags are cut from the answer text.
HISTORY_TAG = re.compile(r"\[\s*(sources?|table|المصادر|المصدر|الجدول)\s*:[^\]]*\]", re.IGNORECASE)
CITATION_MARK = re.compile(r"[ \t]*【[^】]{0,40}】")  # gpt-oss writes "【source1】" or "【4†L1-L3】" after facts


def cell_value(value: object) -> object:
    value = to_plain(value)
    if isinstance(value, str) and NUMBER_TEXT.fullmatch(value.strip()):
        return to_plain(float(value.replace(",", "")))
    return value


def without_history_tags(text: str) -> str:
    """No "[Sources: ...]" tags and no model citation marks ("【source1】"): sources show as chips under the answer."""
    text = CITATION_MARK.sub("", HISTORY_TAG.sub("", text))
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+([.,;:])", r"\1", text)).strip()


def without_markdown_tables(text: str) -> str:
    """Drop markdown table lines from the answer text; the structured table shows the rows once."""
    lines = [line for line in text.splitlines() if not line.lstrip().startswith("|")]
    return "\n".join(lines).strip()


def clean_table(table: dict | None) -> dict | None:
    """Keep a table only when it has columns; make every row the same length as the columns."""
    if not isinstance(table, dict) or not table.get("columns"):
        return None
    columns = [str(column) for column in table["columns"]]
    rows = []
    for row in table.get("rows") or []:
        if isinstance(row, dict):
            row = [row.get(column) for column in columns]
        if not isinstance(row, list):
            continue
        row = [cell_value(value) for value in row[: len(columns)]]
        rows.append(row + [None] * (len(columns) - len(row)))
    return {"columns": columns, "rows": rows} if rows else None


def clean_sources(context: ToolContext, sources: list | None) -> list[Source]:
    """Keep only sources that name a loaded document, using its real file name."""
    names = [document.name for document in context.documents]
    cleaned = []
    for item in sources or []:
        if not isinstance(item, dict):
            continue
        name = best_match(str(item.get("document", "")), names)
        if name is None:
            continue
        source = Source(document=name, location=str(item.get("location", "")), snippet=str(item.get("snippet", "")))
        if source not in cleaned:
            cleaned.append(source)
    return cleaned


def submit_answer(
    context: ToolContext,
    answer: str,
    table: dict | None = None,
    sources: list | None = None,
    table_result_id: str | list | None = None,
    kind: str | None = None,
) -> ToolResult:
    """Check and package the final answer. `table_result_id` ("t1" or "t1,t2") attaches query_table rows
    exactly as computed."""
    answer = without_history_tags(str(answer or ""))
    if not answer:
        raise ToolError("'answer' cannot be empty (and must not be only a [Sources: ...] tag).")
    table_ids = saved_table_ids(table_result_id)
    unknown = [table_id for table_id in table_ids if table_id not in context.saved_tables]
    if unknown:
        saved = ", ".join(context.saved_tables) or "none"
        raise ToolError(f"No saved table '{unknown[0]}'. Saved tables: {saved}")
    if table_ids:
        table = combine_saved_tables(context, table_ids)
    table = clean_table(table)
    text = without_markdown_tables(str(answer)) if table else str(answer).strip()
    final = FinalAnswer(
        answer=text or str(answer).strip(),
        table=table,
        sources=clean_sources(context, sources),
        kind="not_found" if kind == "not_found" else "answer",
    )
    return ToolResult(data={"final_answer": final}, step="Wrote the answer", is_final=True)
