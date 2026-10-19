"""Tool: every date, quarter and time period in the documents, with the sentence around it and its page."""

from AI.tools.date_patterns import find_date_mentions, sentence_around
from AI.tools.lookup import find_document, means_all_documents
from AI.tools.tool_context import ToolContext, ToolResult

MAX_RESULTS = 60


def dates_in_pages(document) -> list[dict]:
    mentions = []
    for page in document.pages:
        for kind, text, start, end in find_date_mentions(page.text):
            mentions.append(
                {
                    "date": text,
                    "kind": kind,
                    "context": sentence_around(page.text, start, end),
                    "document": document.name,
                    "location": f"page {page.number}",
                }
            )
    return mentions


def dates_in_tables(document) -> list[dict]:
    """Date cells in tables (Excel dates are stored as "YYYY-MM-DD" text)."""
    mentions = []
    for table in document.tables:
        for column in table.data.columns:
            if table.data[column].dtype != object:
                continue
            for row_number, value in table.data[column].items():
                if not isinstance(value, str):
                    continue
                for kind, text, _, _ in find_date_mentions(value):
                    if kind == "period":
                        continue
                    row_text = " | ".join(str(v) for v in table.data.loc[row_number].tolist() if v is not None)
                    mentions.append(
                        {
                            "date": text,
                            "kind": kind,
                            "context": f"{column}: {row_text}"[:300],
                            "document": document.name,
                            "location": f"{table.id} · row {row_number}",
                        }
                    )
    return mentions


def group_repeats(mentions: list[dict]) -> list[dict]:
    """The same date text repeated in one document (e.g. "21 days before" on 220 spec pages) becomes one entry."""
    groups: dict[tuple, dict] = {}
    for mention in mentions:
        key = (mention["document"], mention["kind"], mention["date"].lower())
        if key not in groups:
            groups[key] = {**mention, "places": [mention["location"]]}
        else:
            groups[key]["places"].append(mention["location"])
    grouped = []
    for entry in groups.values():
        places = entry.pop("places")
        if len(places) > 1:
            shown = ", ".join(places[:5]) + (f" and {len(places) - 5} more" if len(places) > 5 else "")
            entry["location"] = f"{shown} ({len(places)} times)"
        grouped.append(entry)
    return grouped


def find_dates(context: ToolContext, document: str | None = None) -> ToolResult:
    """All dates and periods in one document, or in every readable document when none is given."""
    if not means_all_documents(document):
        documents = [find_document(context, document)]
    else:
        documents = [d for d in context.documents if d.status == "ok"]
    mentions = []
    for found in documents:
        mentions += dates_in_pages(found) + dates_in_tables(found)
    grouped = group_repeats(mentions)

    data: dict = {"count": len(grouped), "dates": grouped[:MAX_RESULTS]}
    if len(grouped) > MAX_RESULTS:
        data["not_shown"] = f"{len(grouped) - MAX_RESULTS} more. Call find_dates with one document at a time."
    where = documents[0].name if len(documents) == 1 else f"{len(documents)} documents"
    return ToolResult(data=data, step=f"Found {len(grouped)} dates and periods in {where}")
