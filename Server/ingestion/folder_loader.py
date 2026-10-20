"""Load a whole folder: scan it, then read each file on its own so one bad file never stops the rest."""

import logging
from collections.abc import Callable
from pathlib import Path

from Server.ingestion.excel_reader import read_excel
from Server.ingestion.folder_scanner import FoundFile, scan_folder
from Server.ingestion.models import STATUS_CORRUPT, STATUS_EMPTY, STATUS_TOO_LARGE, Document, FolderResult
from Server.ingestion.pdf_reader import read_pdf
from Server.ingestion.word_reader import read_word

logger = logging.getLogger("projectlens")

READERS: dict[str, Callable[[Path, Document], Document]] = {
    "pdf": read_pdf,
    "excel": read_excel,
    "word": read_word,
}


def load_file(found: FoundFile, max_file_mb: float) -> Document:
    """Read one file into a Document with a status. Never raises."""
    size_mb = round(found.path.stat().st_size / (1024 * 1024), 2)
    document = Document(name=found.name, path=str(found.path), file_type=found.file_type, size_mb=size_mb)
    if found.path.stat().st_size == 0:
        document.status = STATUS_EMPTY
        document.message = "This file is empty (0 bytes)."
        return document
    if size_mb > max_file_mb:
        document.status = STATUS_TOO_LARGE
        document.message = f"This file is {size_mb} MB; the limit is {max_file_mb} MB (MAX_FILE_MB in .env)."
        return document
    try:
        return READERS[found.file_type](found.path, document)
    except Exception as error:  # last safety net: a reader bug must not stop the folder
        document.status = STATUS_CORRUPT
        document.message = "This file could not be read."
        logger.warning("Could not read %s: %s", found.name, error)
        return document


def load_folder(
    folder: str | Path,
    max_file_mb: float = 100,
    on_file: Callable[[str], None] | None = None,
) -> FolderResult:
    """Read every supported file. `on_file` is called with each file name before it is read."""
    found_files, skipped = scan_folder(folder)
    documents = []
    for found in found_files:
        if on_file:
            on_file(found.name)
        documents.append(load_file(found, max_file_mb))
    return FolderResult(folder=str(folder), documents=documents, skipped=skipped)
