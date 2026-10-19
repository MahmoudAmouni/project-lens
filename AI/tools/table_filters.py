"""Apply simple filters to a table. A fixed list of operators; nothing from the model is ever run as code."""

import re

import pandas as pd

from AI.tools.lookup import find_column, require_column
from AI.tools.tool_context import TableLike, ToolError

NUMBER_OPERATORS = {">", ">=", "<", "<="}
OPERATORS = NUMBER_OPERATORS | {"=", "!=", "contains"}
SUFFIXES = {"k": 1e3, "m": 1e6, "mn": 1e6, "million": 1e6, "b": 1e9, "bn": 1e9, "billion": 1e9}


def to_number(value: object) -> float:
    """1000000, "1,000,000", "SAR 1M" or "1.5 million" -> a number. ToolError when it is not one."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = re.sub(r"(sar|usd|eur|aed|\$|,|\s)", "", str(value).lower())
    match = re.fullmatch(r"(-?\d+(?:\.\d+)?)([a-z]*)", text)
    if not match or (match.group(2) and match.group(2) not in SUFFIXES):
        raise ToolError(f"'{value}' is not a number.")
    return float(match.group(1)) * SUFFIXES.get(match.group(2), 1)


def column_as_numbers(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return series
    return pd.to_numeric(series, errors="coerce")


def condition(table: TableLike, column: str, operator: str, value: object) -> pd.Series:
    """True/False for each row."""
    series = table.data[column]
    if operator in NUMBER_OPERATORS:
        numbers, limit = column_as_numbers(series), to_number(value)
        return {">": numbers > limit, ">=": numbers >= limit, "<": numbers < limit, "<=": numbers <= limit}[operator]
    if operator == "contains":
        return series.astype(str).str.contains(str(value), case=False, regex=False) & series.notna()
    if pd.api.types.is_numeric_dtype(series):
        matches = series == to_number(value)
    else:
        matches = series.astype(str).str.strip().str.lower() == str(value).strip().lower()
    return matches if operator == "=" else ~matches


def apply_filters(table: TableLike, filters: list[dict]) -> tuple[pd.Series, list[str], str | None]:
    """A row mask for all filters (AND), notes like "used column 'Total Amount (SAR)' for 'amount'",
    and the column of the first number filter (used for grand totals)."""
    mask = pd.Series(True, index=table.data.index)
    notes: list[str] = []
    number_column = None
    for item in filters or []:
        if not isinstance(item, dict) or "column" not in item or "operator" not in item:
            raise ToolError("Each filter needs 'column', 'operator' and 'value'.")
        operator = str(item["operator"]).strip().lower()
        if operator == "==":
            operator = "="
        if operator not in OPERATORS:
            raise ToolError(f"Unknown operator '{item['operator']}'. Use one of: {', '.join(sorted(OPERATORS))}")
        column = require_column(table, item["column"])
        if column != item["column"]:
            notes.append(f"used column '{column}' for '{item['column']}'")
        if operator in NUMBER_OPERATORS and number_column is None:
            number_column = column
        mask &= condition(table, column, operator, item.get("value"))
    return mask.fillna(False), notes, number_column


def filter_columns(table: TableLike, filters: list[dict]) -> bool:
    """True when every filter column exists in the table (used when searching all tables)."""
    return all(isinstance(f, dict) and find_column(table, f.get("column", "")) for f in filters or [])
