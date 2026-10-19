"""Split documents into small pieces for search. A piece never crosses a page, so it has one exact page."""

from dataclasses import dataclass

CHUNK_CHARS = 800
OVERLAP_CHARS = 150
MAX_TABLE_ROWS_INDEXED = 5_000  # per table, for search only; query_table always sees every row


@dataclass
class Chunk:
    text: str
    document: str
    location: str  # "page 14" or "Sheet 'BOQ', rows 12-19"
    page: int = 0  # 0 for table chunks
    table_id: str = ""


def split_text(text: str) -> list[str]:
    """~800 character pieces with 150 overlap, cut at a space when possible."""
    text = " ".join(text.split())
    if len(text) <= CHUNK_CHARS:
        return [text] if text else []
    pieces, start = [], 0
    while start < len(text):
        end = min(start + CHUNK_CHARS, len(text))
        if end < len(text):
            space = text.rfind(" ", start + CHUNK_CHARS // 2, end)
            end = space if space != -1 else end
        pieces.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - OVERLAP_CHARS, start + 1)
    return [piece for piece in pieces if piece]


def page_chunks(document) -> list[Chunk]:
    return [
        Chunk(text=piece, document=document.name, location=f"page {page.number}", page=page.number)
        for page in document.pages
        for piece in split_text(page.text)
    ]


def row_line(row_number: int, row) -> str:
    """One table row as text: "row 47: Item: 3.2 | Description: Structural steel | Amount (SAR): 6450000"."""
    cells = [f"{column}: {value}" for column, value in row.items() if value is not None and str(value) != "nan"]
    return f"row {row_number}: " + " | ".join(cells)


def table_chunks(document) -> list[Chunk]:
    """Table rows grouped into ~800 character pieces, so search can find "steel" inside a BOQ."""
    chunks = []
    for table in document.tables:
        group: list[tuple[int, str]] = []  # (row number, line)
        for row_number, row in table.data.head(MAX_TABLE_ROWS_INDEXED).iterrows():
            line = row_line(int(row_number), row)
            if group and sum(len(text) for _, text in group) + len(line) > CHUNK_CHARS:
                chunks.append(make_table_chunk(document, table, group))
                group = []
            group.append((int(row_number), line))
        if group:
            chunks.append(make_table_chunk(document, table, group))
    return chunks


def make_table_chunk(document, table, group: list[tuple[int, str]]) -> Chunk:
    first_row, last_row = group[0][0], group[-1][0]
    lines = [text for _, text in group]
    where = f"page {table.data.loc[first_row, 'Page']}" if "Page" in table.data.columns else f"Sheet '{table.id}'"
    header = f"Table {table.id} in {document.name}"
    return Chunk(
        text=header + "\n" + "\n".join(lines),
        document=document.name,
        location=f"{where}, rows {first_row}-{last_row}",
        table_id=table.id,
    )


def chunk_document(document) -> list[Chunk]:
    """All search pieces of one readable document."""
    return page_chunks(document) + table_chunks(document)
