"""Save files dropped in the browser into their own folder under .uploads/, so they load like any folder."""

import shutil
import time
import uuid
from pathlib import Path

from fastapi import UploadFile

from Server.config import PROJECT_ROOT

UPLOADS_DIR = PROJECT_ROOT / ".uploads"
KEEP_UPLOADS = 3  # older upload folders are deleted


def safe_name(name: str | None, used: set[str]) -> str:
    """Only the file name (no folders like "../"), made unique inside the upload folder."""
    base = Path(name or "file").name.strip() or "file"
    stem, suffix, number = Path(base).stem, Path(base).suffix, 2
    candidate = base
    while candidate.lower() in used:
        candidate, number = f"{stem} ({number}){suffix}", number + 1
    used.add(candidate.lower())
    return candidate


def remove_old_uploads() -> None:
    folders = sorted((p for p in UPLOADS_DIR.glob("upload_*") if p.is_dir()), key=lambda p: p.name)
    for old in folders[:-KEEP_UPLOADS]:
        shutil.rmtree(old, ignore_errors=True)


def save_uploads(files: list[UploadFile]) -> Path:
    """Write the files to a new folder and return it."""
    # time first so folders sort by age; a random part keeps two uploads in the same second apart
    folder = UPLOADS_DIR / f"upload_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    folder.mkdir(parents=True, exist_ok=True)
    used: set[str] = set()
    for upload in files:
        with (folder / safe_name(upload.filename, used)).open("wb") as target:
            shutil.copyfileobj(upload.file, target, length=1024 * 1024)
    remove_old_uploads()
    return folder
