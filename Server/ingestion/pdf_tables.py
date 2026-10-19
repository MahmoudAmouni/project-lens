"""Pull tables out of PDF pages with pdfplumber, and join tables that continue on the next page."""

from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber
import pymupdf

from Server.ingestion.models import Table
from Server.ingestion.table_cleaner import clean_table

MIN_RULING_LINES = 6  # pages with fewer drawn lines almost never hold a ruled table
MAX_TABLE_PAGES = 400  # safety limit for very large PDFs


@dataclass
class RawTable:
    """A table as pdfplumber found it, with the page of every row."""

    rows: list[list[object]]
    row_pages: list[int]
    width: int
    position_on_page: int  # 1 = first table on its page
    is_last_on_page: bool = False
    pages: list[int] = field(default_factory=list)


def pages_with_ruling_lines(pdf: pymupdf.Document) -> list[int]:
    """1-based page numbers that have enough drawn lines to hold a table."""
    numbers = []
    for page in pdf:
        if len(page.get_drawings()) >= MIN_RULING_LINES:
            numbers.append(page.number + 1)
        if len(numbers) >= MAX_TABLE_PAGES:
            break
    return numbers


def extract_raw_tables(path: Path, page_numbers: list[int]) -> list[RawTable]:
    """Run pdfplumber only on the given pages."""
    raw_tables: list[RawTable] = []
    with pdfplumber.open(path) as pdf:
        for number in page_numbers:
            found = [t for t in pdf.pages[number - 1].extract_tables() if t and len(t) >= 2]
            for position, rows in enumerate(found, start=1):
                width = max(len(row) for row in rows)
                raw_tables.append(
                    RawTable(
                        rows=rows,
                        row_pages=[number] * len(rows),
                        width=width,
                        position_on_page=position,
                        is_last_on_page=position == len(found),
                        pages=[number],
                    )
                )
    return raw_tables


def continues(previous: RawTable, current: RawTable) -> bool:
    """True when `current` is the same table carried over to the next page."""
    return (
        previous.is_last_on_page
        and current.position_on_page == 1
        and current.pages[0] == previous.pages[-1] + 1
        and current.width == previous.width
    )


def merge_continued_tables(raw_tables: list[RawTable]) -> list[RawTable]:
    """Join tables that run over several pages into one."""
    merged: list[RawTable] = []
    for table in raw_tables:
        if merged and continues(merged[-1], table):
            last = merged[-1]
            last.rows += table.rows
            last.row_pages += table.row_pages
            last.pages.append(table.pages[0])
            last.is_last_on_page = table.is_last_on_page
        else:
            merged.append(table)
    return merged


def to_table(raw: RawTable, number_on_first_page: int) -> Table | None:
    """Clean a raw table and add a "Page" column so every row can be cited."""
    cleaned = clean_table(raw.rows)
    if cleaned is None:
        return None
    data = cleaned.data
    page_column = "Page" if "Page" not in data.columns else "Source page"
    data.insert(0, page_column, [raw.row_pages[row_number - 1] for row_number in data.index])
    first, last = raw.pages[0], raw.pages[-1]
    location = f"page {first}" if first == last else f"pages {first}-{last}"
    return Table(
        id=f"page_{first}_table_{number_on_first_page}",
        data=data,
        location=location,
        currencies=cleaned.currencies,
        summary_rows=cleaned.summary_rows,
    )


def read_pdf_tables(path: Path, pdf: pymupdf.Document) -> list[Table]:
    """All clean tables in the PDF."""
    candidate_pages = pages_with_ruling_lines(pdf)
    if not candidate_pages:
        return []
    tables: list[Table] = []
    for raw in merge_continued_tables(extract_raw_tables(path, candidate_pages)):
        table = to_table(raw, raw.position_on_page)
        if table is not None:
            tables.append(table)
    return tables
