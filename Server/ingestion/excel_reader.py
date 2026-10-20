"""Read every sheet of an Excel file into a clean table, and decide the file status."""

import logging
from pathlib import Path

import openpyxl
import pandas as pd
from openpyxl.worksheet.worksheet import Worksheet

from Server.ingestion.models import STATUS_CORRUPT, STATUS_EMPTY, STATUS_ENCRYPTED, Document, Table
from Server.ingestion.money_parser import currency_in_notes
from Server.ingestion.table_cleaner import clean_table
from Server.ingestion.table_splitter import split_tables

logger = logging.getLogger("projectlens")

OLE_SIGNATURE = b"\xd0\xcf\x11\xe0"  # old .xls files and password protected .xlsx files start with this
NOTE_ROWS = 12  # title and note rows (e.g. "All prices in USD") are looked for in the first rows
FAST_MODE_MB = 2  # bigger files are read with calamine (much faster, but merged cells are not filled)


def is_ole_file(path: Path) -> bool:
    """True for files in the old binary Office format."""
    with path.open("rb") as file:
        return file.read(4) == OLE_SIGNATURE


def fill_merged_cells(sheet: Worksheet) -> None:
    """Copy the value of each merged block into all of its cells."""
    for merged in list(sheet.merged_cells.ranges):
        value = sheet.cell(merged.min_row, merged.min_col).value
        sheet.unmerge_cells(str(merged))
        for row in range(merged.min_row, merged.max_row + 1):
            for column in range(merged.min_col, merged.max_col + 1):
                sheet.cell(row, column).value = value


def read_xlsx_sheets(path: Path, size_mb: float) -> dict[str, list[list[object]]]:
    """Sheet name -> rows of raw cell values, starting from Excel row 1.

    Small files: openpyxl, which can fill merged cells. Big files: calamine (about 10x faster)."""
    if size_mb > FAST_MODE_MB:
        return read_with_pandas(path, engine="calamine")
    workbook = openpyxl.load_workbook(path, data_only=True)
    try:
        sheets = {}
        for sheet in workbook.worksheets:
            fill_merged_cells(sheet)
            sheets[sheet.title] = [list(row) for row in sheet.iter_rows(min_row=1, values_only=True)]
        return sheets
    finally:
        workbook.close()


def read_with_pandas(path: Path, engine: str) -> dict[str, list[list[object]]]:
    """All sheets as raw rows from row 1 (blank rows are kept, so row numbers stay exact)."""
    frames = pd.read_excel(path, sheet_name=None, header=None, dtype=object, engine=engine)
    return {name: frame.astype(object).where(frame.notna(), None).values.tolist() for name, frame in frames.items()}


def note_texts(rows: list[list[object]]) -> list[str]:
    """Title and note rows at the top of a sheet: rows holding one text only (a merged title repeats it)."""
    texts = []
    for row in rows[:NOTE_ROWS]:
        values = {str(cell).strip() for cell in row if cell is not None and str(cell).strip()}
        if len(values) == 1:
            texts.append(values.pop())
    return texts


def sheet_to_tables(sheet_name: str, rows: list[list[object]]) -> list[Table]:
    """Clean one sheet into one table, or several when it holds separate tables. Row numbers stay exact."""
    parts = split_tables(rows)
    note_currency = currency_in_notes([sheet_name, *note_texts(rows)])  # "All prices in US Dollars" above
    tables = []
    for number, (part_rows, row_numbers) in enumerate(parts, start=1):
        cleaned = clean_table(part_rows, row_numbers=row_numbers, note_currency=note_currency)
        if cleaned is None:
            continue
        first, last = cleaned.data.index[0], cleaned.data.index[-1]
        tables.append(
            Table(
                id=sheet_name if len(parts) == 1 else f"{sheet_name} (table {number})",
                data=cleaned.data,
                location=f"Sheet '{sheet_name}', rows {first}-{last}",
                currencies=cleaned.currencies,
                summary_rows=cleaned.summary_rows,
            )
        )
    return tables


def read_excel(path: Path, document: Document) -> Document:
    """Fill `document` with one table per non-empty sheet. Never raises."""
    old_format = is_ole_file(path)
    if old_format and path.suffix.lower() != ".xls":
        document.status = STATUS_ENCRYPTED
        document.message = "This Excel file is password protected."
        return document

    try:
        sheets = read_with_pandas(path, "xlrd") if old_format else read_xlsx_sheets(path, document.size_mb)
    except Exception as error:
        document.status = STATUS_CORRUPT
        document.message = "This Excel file is damaged or is not a real Excel file."
        logger.warning("Could not read %s: %s", path.name, error)
        return document

    document.tables = [table for name, rows in sheets.items() for table in sheet_to_tables(name, rows)]
    if not document.tables:
        document.status = STATUS_EMPTY
        document.message = "All sheets in this file are blank."
    return document
