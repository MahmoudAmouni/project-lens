"""Read a PDF into pages of text plus tables, and decide its status."""

import logging
import unicodedata
from pathlib import Path

import pymupdf

from Server.ingestion.models import (
    STATUS_CORRUPT,
    STATUS_EMPTY,
    STATUS_ENCRYPTED,
    STATUS_SCANNED,
    Document,
    Page,
)
from Server.ingestion.pdf_tables import read_pdf_tables

logger = logging.getLogger("projectlens")

MIN_TEXT_PER_PAGE = 20  # fewer characters than this means the page is probably a scanned image


def open_pdf(path: Path) -> pymupdf.Document:
    """Open the PDF; raises when the file is not a valid PDF."""
    return pymupdf.open(path, filetype="pdf")


def clean_text(text: str) -> str:
    """NFKC turns Arabic display letter shapes and ligatures back into normal letters."""
    return unicodedata.normalize("NFKC", text).strip()


def read_pages(pdf: pymupdf.Document) -> list[Page]:
    """Text of every page, 1-based numbers."""
    return [Page(number=page.number + 1, text=clean_text(page.get_text("text"))) for page in pdf]


def read_pdf(path: Path, document: Document) -> Document:
    """Fill `document` with pages, tables and status. Never raises."""
    try:
        pdf = open_pdf(path)
    except Exception as error:
        document.status = STATUS_CORRUPT
        document.message = "This file is not a valid PDF or is damaged."
        logger.warning("Could not open %s: %s", path.name, error)
        return document

    with pdf:
        if pdf.needs_pass and not pdf.authenticate(""):
            document.status = STATUS_ENCRYPTED
            document.message = "This PDF is password protected."
            return document
        if pdf.page_count == 0:
            document.status = STATUS_EMPTY
            document.message = "This PDF has no pages."
            return document

        document.pages = read_pages(pdf)
        empty_pages = [p.number for p in document.pages if len(p.text) < MIN_TEXT_PER_PAGE]
        if len(empty_pages) == len(document.pages):
            document.status = STATUS_SCANNED
            document.message = "No readable text: probably a scanned PDF (OCR is not supported yet)."
            return document

        try:
            document.tables = read_pdf_tables(path, pdf)
        except Exception as error:
            document.message = "Text was read, but the tables could not be extracted."
            logger.warning("Tables failed in %s: %s", path.name, error)

    if empty_pages and not document.message:
        document.message = describe_empty_pages(empty_pages)
    return document


def describe_empty_pages(numbers: list[int]) -> str:
    """Short note like "Pages 3, 7 have no readable text (probably scanned)."."""
    shown = ", ".join(str(n) for n in numbers[:10])
    more = f" and {len(numbers) - 10} more" if len(numbers) > 10 else ""
    label = "Page" if len(numbers) == 1 else "Pages"
    verb = "has" if len(numbers) == 1 else "have"
    return f"{label} {shown}{more} {verb} no readable text (probably scanned)."
