"""Read query_table arguments in the shapes different models write them, before any filtering happens.

Every model is asked for filters=[{"column", "operator", "value"}], but some send the list as JSON text,
a plain {"Milestone": 3}, {"Amount": {">": 1000000}}, "op"/"field" instead of "operator"/"column",
or columns as text ('["Amount"]', "Item, Amount"). These all become the one shape the filters expect.
"""

import json

from AI.tools.tool_context import ToolError

FILTER_HELP = 'Write filters as [{"column": "Amount", "operator": ">", "value": 1000000}].'
COLUMN_KEYS = ("column", "field", "name", "col")
OPERATOR_KEYS = ("operator", "op", "comparison")
OPERATORS = (">", ">=", "<", "<=", "=", "==", "!=", "contains")


def from_json_text(value: object) -> object:
    """'[{...}]' or '{...}' -> the parsed value; anything else is returned as it is."""
    if isinstance(value, str) and value.strip()[:1] in ("[", "{"):
        try:
            return json.loads(value)
        except ValueError as error:
            raise ToolError(f"Could not read {value[:80]!r} as JSON. {FILTER_HELP}") from error
    return value


def first_of(item: dict, keys: tuple[str, ...]) -> object:
    return next((item[key] for key in keys if key in item), None)


def shorthand_filters(item: dict) -> list[dict]:
    """{"Milestone": 3} -> Milestone = 3; {"Amount": {">": 1000000}} -> Amount > 1000000."""
    filters = []
    for column, value in item.items():
        value = from_json_text(value)
        if isinstance(value, dict) and len(value) == 1 and next(iter(value)) in OPERATORS:
            operator, value = next(iter(value.items()))
            filters.append({"column": column, "operator": operator, "value": value})
        else:
            filters.append({"column": column, "operator": "=", "value": value})
    return filters


def one_filter(item: object) -> list[dict]:
    item = from_json_text(item)
    if isinstance(item, list):
        return [found for part in item for found in one_filter(part)]
    if not isinstance(item, dict):
        raise ToolError(f"Each filter needs 'column', 'operator' and 'value'. {FILTER_HELP}")
    column = first_of(item, COLUMN_KEYS)
    if column is None:
        return shorthand_filters(item)
    operator = first_of(item, OPERATOR_KEYS)
    return [{"column": str(column), "operator": "=" if operator is None else operator, "value": item.get("value")}]


def normal_filters(filters: object) -> list[dict]:
    """Any of the shapes above -> [{"column", "operator", "value"}]. Raises ToolError for anything else."""
    filters = from_json_text(filters)
    if filters in (None, "", [], {}):
        return []
    if isinstance(filters, dict):
        return one_filter(filters)
    if not isinstance(filters, list):
        raise ToolError(f"'filters' must be a list. {FILTER_HELP}")
    return [found for item in filters for found in one_filter(item)]


def normal_columns(columns: object) -> list[str] | None:
    """'["Item", "Amount"]', "Item, Amount" or ["Item"] -> a list of column names; None when not given."""
    columns = from_json_text(columns)
    if columns in (None, "", []):
        return None
    if isinstance(columns, str):
        return [name.strip() for name in columns.split(",") if name.strip()]
    if isinstance(columns, list):
        return [str(name) for name in columns]
    raise ToolError("'columns' must be a list of column names.")


def normal_flag(value: object, default: bool) -> bool:
    """true/false, also when written as text ("false", "no", "0")."""
    if isinstance(value, str):
        return value.strip().lower() not in ("false", "no", "0", "")
    return default if value is None else bool(value)
