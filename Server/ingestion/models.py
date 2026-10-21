"""Data classes that every loaded file is turned into."""

from dataclasses import dataclass, field

import pandas as pd

STATUS_OK = "ok"
STATUS_EMPTY = "empty"
STATUS_CORRUPT = "corrupt"
STATUS_ENCRYPTED = "encrypted"
STATUS_SCANNED = "scanned"
STATUS_TOO_LARGE = "too_large"


@dataclass
class Page:
    """One PDF or Word page. `number` is 1-based, like in a PDF viewer."""

    number: int
    text: str


@dataclass
class Table:
    """A cleaned table: an Excel sheet or a table found in a PDF or Word file."""

    id: str  # "BOQ" for an Excel sheet, "page_5_table_1" for a PDF table
    data: pd.DataFrame  # real header row, numbers as numbers; index = row number in the file
    location: str  # human text: "Sheet 'BOQ', rows 5-340" or "page 5"
    currencies: dict[str, str] = field(default_factory=dict)  # column -> "SAR", "USD", ...
    summary_rows: list[int] = field(default_factory=list)  # "Total" rows, left out of sums
    notes: list[str] = field(default_factory=list)  # title lines above the header: "Revision A (SUPERSEDED)"


@dataclass
class Document:
    """One file in the folder, with its read status."""

    name: str
    path: str
    file_type: str  # "pdf", "excel" or "word"
    status: str = STATUS_OK
    message: str = ""  # human explanation when status is not ok
    pages: list[Page] = field(default_factory=list)  # empty for Excel
    tables: list[Table] = field(default_factory=list)
    size_mb: float = 0.0

    @property
    def is_readable(self) -> bool:
        """True when the AI can use this file."""
        return self.status == STATUS_OK

    def find_table(self, table_id: str) -> Table | None:
        """Return the table with this id, ignoring case, or None."""
        wanted = table_id.strip().lower()
        return next((t for t in self.tables if t.id.lower() == wanted), None)


@dataclass
class SkippedFile:
    """A file in the folder that is not a PDF, Excel or Word file."""

    name: str
    reason: str


@dataclass
class FolderResult:
    """Everything found in one folder."""

    folder: str
    documents: list[Document]
    skipped: list[SkippedFile]
