"""Terminal version of ProjectLens (backup for the demo).

Run: python -m Server.cli ./sample_docs
"""

import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table as RichTable

from AI.agent import Agent, AgentAnswer
from AI.errors import AIRateLimitedError, AIUnavailableError
from AI.llm_client import LLMClient
from AI.rag.vector_store import VectorStore
from Server.config import load_settings, project_path
from Server.ingestion.folder_loader import load_folder
from Server.ingestion.folder_scanner import FolderNotFoundError
from Server.ingestion.models import FolderResult

STATUS_STYLE = {"ok": "green", "scanned": "yellow", "too_large": "yellow", "empty": "yellow"}
console = Console()


def show_folder(result: FolderResult) -> None:
    table = RichTable(title=f"Documents in {result.folder}", show_lines=False)
    for column in ("File", "Status", "Pages", "Tables", "Note"):
        table.add_column(column)
    for doc in result.documents:
        style = STATUS_STYLE.get(doc.status, "red")
        tables = ", ".join(f"{t.id} ({len(t.data)} rows)" for t in doc.tables)
        table.add_row(doc.name, f"[{style}]{doc.status}[/]", str(len(doc.pages) or ""), tables, doc.message[:60])
    console.print(table)
    for skipped in result.skipped:
        console.print(f"[dim]Skipped {skipped.name}: {skipped.reason}[/]")


def build_index(settings, result: FolderResult) -> VectorStore | None:
    """Search index; the app still works (without search) if this fails."""
    try:
        store = VectorStore(settings.chroma_dir)
        with console.status("Building the search index (first time can take a minute)..."):
            stats = store.index(result.folder, result.documents)
        console.print(f"[dim]Search index ready: {stats['embedded']} files embedded, {stats['reused']} reused.[/]")
        return store
    except Exception as error:
        console.print(f"[yellow]Search is off: {error}[/]")
        return None


def show_answer(answer: AgentAnswer) -> None:
    console.print(Markdown(answer.answer))
    if answer.table:
        table = RichTable(*answer.table["columns"])
        for row in answer.table["rows"]:
            table.add_row(*[f"{v:,}" if isinstance(v, (int, float)) else str(v or "") for v in row])
        console.print(table)
    for source in answer.sources:
        console.print(f"[cyan]  ▸ {source['document']} · {source['location']}[/]")
    if answer.steps:
        console.print(f"[dim]  How I found this: {' → '.join(answer.steps)}[/]")


def chat(agent: Agent) -> None:
    history: list[dict] = []
    console.print("\n[bold]Ask a question[/] (type 'exit' to quit).")
    while True:
        try:
            question = console.input("\n[bold cyan]> [/]").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in ("exit", "quit"):
            break
        if not question:
            continue
        try:
            with console.status("Thinking..."):
                answer = agent.ask(question, history)
        except (AIUnavailableError, AIRateLimitedError) as error:
            console.print(f"[red]{error}[/]")
            continue
        except Exception as error:
            console.print(f"[red]Something went wrong: {error}[/]")
            continue
        show_answer(answer)
        history += [{"role": "user", "content": question}, {"role": "assistant", "content": answer.answer}]


def main() -> None:
    settings = load_settings()
    folder = project_path(sys.argv[1]) if len(sys.argv) > 1 else settings.docs_folder
    if not folder:
        console.print("[red]Give a folder: python -m Server.cli ./sample_docs[/]")
        return
    try:
        with console.status(f"Reading {folder}..."):
            result = load_folder(folder, settings.max_file_mb)
    except FolderNotFoundError as error:
        console.print(f"[red]{error}[/]")
        return
    show_folder(result)
    if not any(doc.is_readable for doc in result.documents):
        console.print("[yellow]No readable PDF, Excel or Word files in this folder.[/]")
        return
    try:
        llm = LLMClient(settings.groq_api_key, settings.model, settings.fallback_model)
    except AIUnavailableError as error:
        console.print(f"[red]{error}[/]")
        return
    agent = Agent(llm, result.documents, build_index(settings, result))
    console.print(f"[dim]Model: {settings.model} (backup: {settings.fallback_model})[/]")
    chat(agent)


if __name__ == "__main__":
    main()
