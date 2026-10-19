"""Shared pieces for every tool: what a document looks like, the tool context and the tool result.

The AI folder never imports from Server. The Server passes in objects that have these fields.
"""

import json
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

import pandas as pd

MAX_RESULT_CHARS = 6_000  # Groq free tier: ~8,000 tokens per minute, so results stay small


class PageLike(Protocol):
    number: int
    text: str


class TableLike(Protocol):
    id: str
    data: pd.DataFrame  # index = row number in the file
    location: str
    currencies: dict[str, str]
    summary_rows: list[int]


class DocumentLike(Protocol):
    name: str
    path: str
    file_type: str
    status: str
    message: str
    pages: list[PageLike]
    tables: list[TableLike]


class ToolError(Exception):
    """A clear problem with the tool call; the message is sent back to the model so it can fix it."""


@dataclass
class ToolContext:
    """Everything a tool can use."""

    documents: Sequence[DocumentLike]
    vector_store: Any = None  # AI.rag.vector_store.VectorStore, or None when RAG is off
    saved_tables: dict[str, dict] = field(default_factory=dict)  # query_table rows, by table_result_id


@dataclass
class ToolResult:
    data: dict  # sent to the model as JSON
    step: str  # human text for "How I found this", e.g. "Filtered BOQ.xlsx: 14 rows"
    is_final: bool = False  # True only for submit_answer


@dataclass
class Source:
    document: str
    location: str
    snippet: str = ""

    def to_dict(self) -> dict:
        return {"document": self.document, "location": self.location, "snippet": self.snippet}


@dataclass
class FinalAnswer:
    answer: str
    table: dict | None = None
    sources: list[Source] = field(default_factory=list)


def to_plain(value: Any) -> Any:
    """Turn numpy/pandas values into plain JSON values; 1250000.0 -> 1250000, NaN -> None."""
    if value is None:
        return None
    if hasattr(value, "item"):  # numpy scalar
        value = value.item()
    if isinstance(value, float):
        if math.isnan(value):
            return None
        return int(value) if value.is_integer() else round(value, 4)
    if isinstance(value, (pd.Timestamp,)):
        return value.strftime("%Y-%m-%d")
    return value


def to_json(data: dict) -> str:
    """JSON for the model, cut to MAX_RESULT_CHARS so one huge result never floods the context."""
    text = json.dumps(data, ensure_ascii=False, default=str)
    if len(text) <= MAX_RESULT_CHARS:
        return text
    return text[:MAX_RESULT_CHARS] + ' ..."[result cut: too long. Ask for fewer rows, pages or columns.]"'
