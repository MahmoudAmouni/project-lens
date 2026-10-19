"""Load a folder of documents and list what was loaded."""

from typing import Annotated

from fastapi import APIRouter, File, Request, UploadFile

from Server.errors import ApiError
from Server.ingestion.upload_store import save_uploads
from Server.schemas.document_schemas import DocumentsResponse, LoadFolderRequest
from Server.state import AppState

router = APIRouter(tags=["documents"])


def documents_response(state: AppState) -> DocumentsResponse:
    return DocumentsResponse.build(
        state.folder, search_ready=state.vector_store is not None, loading=state.loading_folder is not None
    )


@router.post("/documents/load")
def load_documents(body: LoadFolderRequest, request: Request) -> DocumentsResponse:
    """Read every PDF and Excel file in the folder. Each file gets a status; bad files never stop the rest."""
    state: AppState = request.app.state.lens
    state.load(body.folder_path)
    return documents_response(state)


@router.get("/documents")
def list_documents(request: Request) -> DocumentsResponse:
    """The documents loaded right now (empty list before a folder is loaded)."""
    return documents_response(request.app.state.lens)


@router.post("/documents/upload")
def upload_documents(request: Request, files: Annotated[list[UploadFile], File()]) -> DocumentsResponse:
    """Files dropped in the browser: saved to their own folder under .uploads/, then loaded like a folder."""
    if not files:
        raise ApiError("INVALID_REQUEST", "Choose at least one file to upload.", 422)
    state: AppState = request.app.state.lens
    state.load(str(save_uploads(files)))
    return documents_response(state)
