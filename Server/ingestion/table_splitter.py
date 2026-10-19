"""Split one sheet into several tables when they are separated by blank rows and each has its own header.

A gap alone is not enough: BOQs often leave blank rows between sections of the same table. A block
after a gap becomes a new table only when it starts with a header row that differs from the last one.
"""

from Server.ingestion.table_cleaner import find_header_row, tidy_cell

MIN_GAP_ROWS = 2  # blank rows needed between two tables
HEADER_WITHIN_ROWS = 3  # a new table's header must be in its first rows


def is_blank(row: list[object]) -> bool:
    return all(tidy_cell(cell) is None for cell in row)


def blocks(rows: list[list[object]]) -> list[tuple[int, int]]:
    """(start, end) index ranges of rows separated by at least MIN_GAP_ROWS blank rows."""
    ranges, start, blank_run = [], None, 0
    for index, row in enumerate(rows):
        if is_blank(row):
            blank_run += 1
            continue
        if start is None:
            start = index
        elif blank_run >= MIN_GAP_ROWS:
            ranges.append((start, index - blank_run))
            start = index
        blank_run = 0
    if start is not None:
        ranges.append((start, len(rows) - blank_run))
    return ranges


def header_of(rows: list[list[object]]) -> tuple | None:
    """The block's header row (as text), when it starts with one."""
    grid = [[tidy_cell(cell) for cell in row] for row in rows[:HEADER_WITHIN_ROWS] if not is_blank(row)]
    if not grid:
        return None
    width = max(sum(cell is not None for cell in row) for row in grid)
    index = find_header_row(grid, width)
    return tuple(str(cell) for cell in grid[index] if cell is not None) if index is not None else None


def split_tables(rows: list[list[object]]) -> list[tuple[list[list[object]], list[int]]]:
    """[(rows, row_numbers)] for each table in the sheet. Row numbers are 1-based sheet rows."""
    tables: list[tuple[int, int]] = []
    last_header = None
    for start, end in blocks(rows):
        header = header_of(rows[start:end])
        new_table = header is not None and last_header is not None and header != last_header
        if tables and not new_table:
            tables[-1] = (tables[-1][0], end)  # title rows above a table, or the same table after a gap
        else:
            tables.append((start, end))
        last_header = header if header is not None else last_header
    return [(rows[start:end], list(range(start + 1, end + 1))) for start, end in tables]
