"""Turn a raw grid of cells (from Excel or a PDF table) into a clean table.

Steps: tidy cells, find the real header row, drop empty rows and columns,
convert number columns, and flag "Total" rows so sums never count them twice.
"""

import itertools
import re
from dataclasses import dataclass, field
from datetime import date, datetime

import pandas as pd

from Server.ingestion.money_parser import detect_currency, parse_number

HEADER_SEARCH_ROWS = 30  # the header is looked for in the first rows only
NUMERIC_SHARE = 0.8  # a column is numeric when 80% of its cells are numbers
CURRENCY_SAMPLE_CELLS = 200  # cells checked for a currency word when the header has none
IDENTIFIER_HEADER = re.compile(r"^(item|no|ref|code|id|#|s/?n|serial|clause|section|البند|رقم)\b", re.I)
SUMMARY_TEXT = re.compile(r"^\s*(sub[\s-]?total|grand total|total|المجموع|الإجمالي|اجمالي)\b", re.I)


@dataclass
class CleanTable:
    """Result of cleaning: the table plus facts the readers turn into a `Table`."""

    data: pd.DataFrame  # index = row number given by the caller (file row number)
    currencies: dict[str, str] = field(default_factory=dict)
    summary_rows: list[int] = field(default_factory=list)


def tidy_cell(value: object) -> object:
    """Strip text, turn blanks into None, dates into "YYYY-MM-DD"."""
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, str):
        text = " ".join(value.split())
        return text or None
    return value


def is_text(value: object) -> bool:
    """True for a cell that holds words, not a number."""
    return value is not None and parse_number(value) is None


def find_header_row(rows: list[list[object]], width: int) -> int | None:
    """Index of the first row that is mostly words and fills enough columns.

    A title merged across the columns ("PROJECT X - BOQ") repeats one text in every cell: never a header."""
    for index, row in enumerate(rows[:HEADER_SEARCH_ROWS]):
        filled = [cell for cell in row if cell is not None]
        if len(filled) < max(2, width * 0.5) or len({str(cell) for cell in filled}) < 2:
            continue
        if sum(is_text(cell) for cell in filled) / len(filled) >= 0.6:
            return index
    return None


def make_column_names(header: list[object]) -> list[str]:
    """Header cells as unique names; blanks become "Column 3"."""
    names: list[str] = []
    for position, cell in enumerate(header, start=1):
        name = str(cell) if cell is not None else f"Column {position}"
        if isinstance(cell, float) and cell.is_integer():
            name = str(int(cell))
        base, copy_number = name, 2
        while name in names:
            name, copy_number = f"{base} ({copy_number})", copy_number + 1
        names.append(name)
    return names


def parse_number_column(name: str, values: pd.Series) -> list[float | None] | None:
    """The column as numbers when it holds amounts or quantities (not codes like item "3.2"), else None.
    Each cell is parsed once."""
    if IDENTIFIER_HEADER.match(name.strip()):
        return None
    parsed = [None if value is None else parse_number(value) for value in values]
    filled = sum(value is not None for value in values)
    numbers = sum(number is not None for number in parsed)
    return parsed if filled and numbers / filled >= NUMERIC_SHARE else None


def find_currency(name: str, values: pd.Series) -> str | None:
    """Currency named in the header, or else in the first text cells (a sample is enough)."""
    found = detect_currency(name)
    if found:
        return found
    texts = (value for value in values if isinstance(value, str))
    for value in itertools.islice(texts, CURRENCY_SAMPLE_CELLS):
        found = detect_currency(value)
        if found:
            return found
    return None


def find_summary_rows(data: pd.DataFrame) -> list[int]:
    """Row numbers of "Total" / "Sub Total" rows (checked column by column, not row by row)."""
    is_summary = pd.Series(False, index=data.index)
    for name in data.columns:
        if data[name].dtype == object:
            text = data[name].where(data[name].map(lambda cell: isinstance(cell, str)))
            is_summary |= text.str.match(SUMMARY_TEXT, na=False)
    return [int(number) for number in data.index[is_summary]]


def clean_table(rows: list[list[object]], row_numbers: list[int] | None = None) -> CleanTable | None:
    """Clean a raw grid. `row_numbers` gives the file row of each raw row. None if empty."""
    if row_numbers is None:
        row_numbers = list(range(1, len(rows) + 1))
    grid = [[tidy_cell(cell) for cell in row] for row in rows]
    keep = [i for i, row in enumerate(grid) if any(cell is not None for cell in row)]
    grid = [grid[i] for i in keep]
    row_numbers = [row_numbers[i] for i in keep]
    if not grid:
        return None

    width = max(len(row) for row in grid)
    grid = [row + [None] * (width - len(row)) for row in grid]
    used_columns = [c for c in range(width) if any(row[c] is not None for row in grid)]
    grid = [[row[c] for c in used_columns] for row in grid]
    width = len(used_columns)

    header_index = find_header_row(grid, width)
    if header_index is None:
        names = [f"Column {i}" for i in range(1, width + 1)]
        body, body_numbers = grid, row_numbers
    else:
        names = make_column_names(grid[header_index])
        body = grid[header_index + 1 :]
        body_numbers = row_numbers[header_index + 1 :]
        header = grid[header_index]
        repeated = [i for i, row in enumerate(body) if row == header]  # header repeated on each PDF page
        body = [row for i, row in enumerate(body) if i not in repeated]
        body_numbers = [n for i, n in enumerate(body_numbers) if i not in repeated]
    if not body:
        return None

    data = pd.DataFrame(body, columns=names, index=body_numbers, dtype=object)
    currencies: dict[str, str] = {}
    for name in names:
        numbers = parse_number_column(name, data[name])
        if numbers is not None:
            currency = find_currency(name, data[name])
            data[name] = pd.Series(numbers, index=data.index, dtype="float64")
            if currency:
                currencies[name] = currency
    return CleanTable(data=data, currencies=currencies, summary_rows=find_summary_rows(data))
