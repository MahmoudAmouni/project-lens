"""Find the PDF, Excel and Word files in a folder. Everything else is reported as skipped."""

from dataclasses import dataclass
from pathlib import Path

from Server.ingestion.models import SkippedFile

PDF_EXTENSIONS = {".pdf"}
EXCEL_EXTENSIONS = {".xlsx", ".xls", ".xlsm"}
WORD_EXTENSIONS = {".docx"}


class FolderNotFoundError(Exception):
    """The folder path does not exist or is not a folder."""


@dataclass
class FoundFile:
    """A supported file, ready to be read."""

    path: Path
    name: str  # path relative to the folder, e.g. "BOQ/Phase1.xlsx"
    file_type: str  # "pdf", "excel" or "word"


def file_type_for(path: Path) -> str | None:
    """Return "pdf", "excel", "word", or None for unsupported files."""
    extension = path.suffix.lower()
    if extension in PDF_EXTENSIONS:
        return "pdf"
    if extension in EXCEL_EXTENSIONS:
        return "excel"
    if extension in WORD_EXTENSIONS:
        return "word"
    return None


def is_hidden_or_temporary(relative_path: Path) -> bool:
    """Office lock files (~$Book.xlsx) and hidden files or folders are ignored silently."""
    return relative_path.name.startswith("~$") or any(part.startswith(".") for part in relative_path.parts)


def scan_folder(folder: str | Path) -> tuple[list[FoundFile], list[SkippedFile]]:
    """List supported files in the folder and its subfolders, sorted by name."""
    root = Path(folder).expanduser()
    if not root.is_dir():
        raise FolderNotFoundError(f"The folder {folder} does not exist.")

    found: list[FoundFile] = []
    skipped: list[SkippedFile] = []
    for path in sorted(root.rglob("*")):
        relative_path = path.relative_to(root)
        if not path.is_file() or is_hidden_or_temporary(relative_path):
            continue
        name = relative_path.as_posix()
        file_type = file_type_for(path)
        if file_type is None:
            extension = path.suffix.lower() or "no extension"
            skipped.append(SkippedFile(name=name, reason=f"Unsupported file type ({extension})"))
        else:
            found.append(FoundFile(path=path, name=name, file_type=file_type))
    return found, skipped
