"""Shapes of chat requests and responses."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

MAX_QUESTION_CHARS = 4000


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_QUESTION_CHARS)] = (
        Field(examples=["List all cost items above SAR 1M"])
    )
    history: list[ChatMessage] = Field(default_factory=list)
    ui_language: Literal["en", "ar"] | None = None  # screen language: only a hint for very short questions
    model: str | None = None  # the model the user picked; the other models stay as backups


class TableData(BaseModel):
    columns: list[str]
    rows: list[list[str | int | float | None]]


class SourceInfo(BaseModel):
    document: str
    location: str
    snippet: str = ""


class ChatResponse(BaseModel):
    answer: str  # markdown
    table: TableData | None = None
    sources: list[SourceInfo]
    steps: list[str]  # "How I found this"
    model: str
    kind: Literal["answer", "not_found", "out_of_scope", "greeting", "clarify"] = "answer"
    style: Literal["en", "ar", "ar-lb", "arabizi"] = "en"  # how the user wrote; the answer uses the same style
    suggestions: list[str] = Field(default_factory=list)  # example questions for greeting / out_of_scope
