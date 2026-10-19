"""Every tool the model can call: its function and its JSON schema (OpenAI / Groq format).

To add a tool: write AI/tools/<name>.py, add it to TOOLS below, and add one line to the system prompt.
"""

from collections.abc import Callable

from AI.tools.describe_table import describe_table
from AI.tools.find_dates import find_dates
from AI.tools.list_documents import list_documents
from AI.tools.query_table import query_table
from AI.tools.read_document import read_document
from AI.tools.search_documents import search_documents
from AI.tools.submit_answer import submit_answer

DOCUMENT = {"type": "string", "description": "File name from list_documents, e.g. 'BOQ_Phase1.xlsx'."}
TABLE_ID = {"type": "string", "description": "Table id from list_documents (sheet name or 'page_5_table_1')."}

FILTER = {
    "type": "object",
    "properties": {
        "column": {"type": "string", "description": "Column name; close names work ('amount')."},
        "operator": {"type": "string", "enum": [">", ">=", "<", "<=", "=", "!=", "contains"]},
        "value": {"type": ["string", "number"], "description": "Number (1000000) or text."},
    },
    "required": ["column", "operator", "value"],
}

SOURCE = {
    "type": "object",
    "properties": {
        "document": {"type": "string"},
        "location": {"type": "string", "description": "'page 14' or 'Sheet BOQ, row 47'."},
        "snippet": {"type": "string", "description": "Short quote from the document."},
    },
    "required": ["document", "location"],
}


def nullable(field: dict) -> dict:
    """Open models often send null for optional fields; Groq rejects that unless the schema allows it."""
    types = field.get("type", [])
    types = types if isinstance(types, list) else [types]
    return {**field, "type": [*types, "null"]} if "null" not in types else field


def schema(name: str, description: str, properties: dict, required: list[str] | None = None) -> dict:
    required = required or []
    properties = {key: field if key in required else nullable(field) for key, field in properties.items()}
    parameters = {"type": "object", "properties": properties, "required": required}
    return {"type": "function", "function": {"name": name, "description": description, "parameters": parameters}}


TOOLS: dict[str, tuple[Callable, dict]] = {
    "list_documents": (
        list_documents,
        schema("list_documents", "List every loaded file with status, pages, tables, columns and currencies.", {}),
    ),
    "search_documents": (
        search_documents,
        schema(
            "search_documents",
            "Semantic search over all text (and table rows). Returns the best matching passages with file and page.",
            {
                "query": {"type": "string", "description": "What to look for, in any words or language."},
                "document": {**DOCUMENT, "description": "Optional: search only this file."},
                "top_k": {"type": "integer", "description": "Number of passages, default 6, max 8."},
            },
            ["query"],
        ),
    ),
    "read_document": (
        read_document,
        schema(
            "read_document",
            "Read the text of PDF pages in order (max 10 pages per call). Use to summarize or get full context.",
            {
                "document": DOCUMENT,
                "start_page": {"type": "integer", "description": "First page, 1-based. Default 1."},
                "end_page": {"type": "integer", "description": "Last page (inclusive)."},
            },
            ["document"],
        ),
    ),
    "describe_table": (
        describe_table,
        schema(
            "describe_table",
            "Column names, types, currencies, row count and first rows of a table. Call before query_table.",
            {"document": DOCUMENT, "table_id": TABLE_ID},
            ["document"],
        ),
    ),
    "query_table": (
        query_table,
        schema(
            "query_table",
            "Exact filter over EVERY row. Returns match count, sums per column (with currency), the first rows "
            "with their source, and a table_result_id. Use for all amounts, totals, counts and thresholds. "
            "Leave out document to search every table in every file at once.",
            {
                "document": {**DOCUMENT, "description": "One file, or leave out / '*' for every table."},
                "table_id": TABLE_ID,
                "filters": {"type": "array", "items": FILTER, "description": "All must match (AND)."},
                "columns": {"type": "array", "items": {"type": "string"}, "description": "Columns to return."},
                "sort_by": {"type": "string"},
                "descending": {"type": "boolean", "description": "Default true (largest first)."},
                "limit": {"type": "integer", "description": "Rows kept, default 50, max 200."},
                "include_total_rows": {"type": "boolean", "description": "Default false."},
            },
        ),
    ),
    "find_dates": (
        find_dates,
        schema(
            "find_dates",
            "Every date, quarter and time period (e.g. 'within 28 days') with its sentence and page.",
            {"document": {**DOCUMENT, "description": "Optional: one file. Leave out for all files."}},
        ),
    ),
    "submit_answer": (
        submit_answer,
        schema(
            "submit_answer",
            "Give the final answer. Always call this last.",
            {
                "answer": {"type": "string", "description": "Markdown answer, key numbers in **bold**."},
                "kind": {
                    "type": "string",
                    "enum": ["answer", "not_found"],
                    "description": "not_found when the documents do not contain the answer. Default answer.",
                },
                "table_result_id": {
                    "type": "string",
                    "description": "Rows of query_table results exactly as computed: 't1', or 't1,t2' for several.",
                },
                "table": {
                    "type": "object",
                    "description": "Only for rows NOT from query_table. Include a Source column.",
                    "properties": {
                        "columns": {"type": "array", "items": {"type": "string"}},
                        "rows": {"type": "array", "items": {"type": "array", "items": {}}},
                    },
                },
                "sources": {"type": "array", "items": SOURCE},
            },
            ["answer", "sources"],
        ),
    ),
}

TOOL_SCHEMAS = [tool_schema for _, tool_schema in TOOLS.values()]
SUBMIT_ONLY_SCHEMAS = [TOOLS["submit_answer"][1]]
