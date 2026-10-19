"""Shapes of document requests and responses."""

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from Server.ingestion.models import Document, FolderResult


class LoadFolderRequest(BaseModel):
    folder_path: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = Field(
        examples=["./sample_docs"]
    )


class TableInfo(BaseModel):
    id: str
    location: str
    rows: int
    columns: list[str]


class DocumentInfo(BaseModel):
    name: str
    file_type: str
    status: str  # ok | empty | corrupt | encrypted | scanned | too_large
    message: str
    pages: int
    tables: list[TableInfo]
    size_mb: float

    @classmethod
    def from_document(cls, document: Document) -> "DocumentInfo":
        tables = [
            TableInfo(id=t.id, location=t.location, rows=len(t.data), columns=[str(c) for c in t.data.columns])
            for t in document.tables
        ]
        return cls(
            name=document.name,
            file_type=document.file_type,
            status=document.status,
            message=document.message,
            pages=len(document.pages),
            tables=tables,
            size_mb=document.size_mb,
        )


class SkippedInfo(BaseModel):
    name: str
    reason: str


class DocumentsResponse(BaseModel):
    folder: str | None
    documents: list[DocumentInfo]
    skipped: list[SkippedInfo]
    readable_count: int
    search_ready: bool
    loading: bool = False  # True while DOCS_FOLDER is still being read at start-up

    @classmethod
    def build(cls, result: FolderResult | None, search_ready: bool, loading: bool = False) -> "DocumentsResponse":
        if result is None:
            return cls(folder=None, documents=[], skipped=[], readable_count=0, search_ready=False, loading=loading)
        documents = [DocumentInfo.from_document(document) for document in result.documents]
        return cls(
            folder=result.folder,
            documents=documents,
            skipped=[SkippedInfo(name=s.name, reason=s.reason) for s in result.skipped],
            readable_count=sum(d.status == "ok" for d in documents),
            search_ready=search_ready,
            loading=loading,
        )
