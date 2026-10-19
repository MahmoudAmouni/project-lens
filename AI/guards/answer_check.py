"""No source, no answer: the last check before an answer reaches the user.

An answer without sources gets the sources the agent actually read through its tools. If the agent read
nothing, the answer is replaced with a fixed "not found" reply, so a made-up answer never gets through.
"""

MAX_AUTO_SOURCES = 5
SNIPPET_CHARS = 160


def sources_from_tool(name: str, data: dict) -> list[dict]:
    """The document locations a tool result came from."""
    if name == "query_table":
        return [{"document": t["document"], "location": t["location"], "snippet": ""} for t in data.get("tables", [])
                if t.get("match_count")]  # fmt: skip
    if name == "read_document" and data.get("pages"):
        first, last = data["pages"][0]["page"], data["pages"][-1]["page"]
        location = f"page {first}" if first == last else f"pages {first}-{last}"
        return [{"document": data["document"], "location": location, "snippet": ""}]
    if name == "search_documents":
        return [{"document": m["document"], "location": m["location"], "snippet": m["text"][:SNIPPET_CHARS]}
                for m in data.get("matches", [])[:3]]  # fmt: skip
    if name == "find_dates":
        return [{"document": d["document"], "location": d["location"], "snippet": d["context"][:SNIPPET_CHARS]}
                for d in data.get("dates", [])[:3]]  # fmt: skip
    return []


def has_sources(answer) -> bool:
    table = answer.table or {}
    return bool(answer.sources) or "Source" in table.get("columns", [])


def check_answer(answer, consulted: list[dict], not_found_text: str):
    """Make sure an "answer" has sources; returns the (possibly changed) AgentAnswer."""
    if answer.kind != "answer" or has_sources(answer):
        return answer
    unique = list({(s["document"], s["location"]): s for s in consulted}.values())
    if unique:
        answer.sources = unique[:MAX_AUTO_SOURCES]
        return answer
    answer.kind = "not_found"
    answer.answer = not_found_text
    answer.table = None
    return answer
