"""Holds the loaded documents, the search index and the agent in memory (one app, one folder at a time)."""

import logging
import threading
from pathlib import Path

from AI.agent import Agent, AgentAnswer
from AI.llm_client import LLMClient
from AI.rag.vector_store import VectorStore
from AI.router import Router
from AI.usage_tracker import UsageTracker
from Server.config import Settings, project_path
from Server.errors import folder_empty, folder_not_found, no_documents_loaded
from Server.ingestion.folder_loader import load_folder
from Server.ingestion.folder_scanner import FolderNotFoundError
from Server.ingestion.models import FolderResult

logger = logging.getLogger("projectlens")


def clean_folder_path(text: str) -> str:
    """Accept paths pasted with quotes ("C:\\docs") or relative to the project folder."""
    return project_path(text.strip().strip('"').strip("'"))


def make_router(settings: Settings, usage: UsageTracker) -> Router:
    """The router waits at most a few seconds for a rate limit, then falls back to the script check."""
    main, *backups = [name.strip() for name in settings.router_model.split(",") if name.strip()] or [""]
    if not main:
        return Router()
    llm = LLMClient(
        settings.groq_api_key, main, ",".join(backups), reasoning_effort="low", max_wait_seconds=10, usage=usage
    )
    return Router(llm)


class AppState:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.folder: FolderResult | None = None
        self.vector_store: VectorStore | None = None
        self.agent: Agent | None = None
        self.llm = None  # created on the first question, so a missing key never blocks loading files
        self.router: Router | None = None
        self.usage = UsageTracker(settings.usage_file)  # shared by the agent and the router: same Groq limits
        self.use_search = True  # tests switch this off to skip embedding
        self.loading_folder: str | None = None
        self.loading_step: str | None = None  # "Reading BOQ.xlsx", shown in the Client while a folder loads
        self._load_lock = threading.Lock()
        self._chat_lock = threading.Lock()  # one question at a time: the agent keeps per-question state

    @property
    def readable_count(self) -> int:
        return sum(document.is_readable for document in self.folder.documents) if self.folder else 0

    def load(self, folder_text: str) -> FolderResult:
        """Read a folder, build its search index and a fresh agent. Raises ApiError with a clear code."""
        folder = clean_folder_path(folder_text)
        with self._load_lock:
            self.loading_folder = folder
            try:
                try:
                    result = load_folder(folder, self.settings.max_file_mb, on_file=self.show_reading)
                except FolderNotFoundError as error:
                    raise folder_not_found(str(error)) from error
                if not result.documents:
                    skipped = f" ({len(result.skipped)} other files were skipped)" if result.skipped else ""
                    raise folder_empty(f"There are no PDF, Excel or Word files in {folder}{skipped}.")
                self.loading_step = "Building the search index"
                store = self.build_index(result)
                # switch everything at once, so a question never sees new documents with the old index
                self.folder, self.vector_store, self.agent = result, store, None
                return result
            finally:
                self.loading_folder = self.loading_step = None

    def show_reading(self, name: str) -> None:
        self.loading_step = f"Reading {name}"

    def build_index(self, result: FolderResult) -> VectorStore | None:
        """The app still works without search (exact tools only) if indexing fails."""
        if not self.use_search:
            return None
        try:
            store = VectorStore(self.settings.chroma_dir)
            stats = store.index(result.folder, result.documents)
            logger.info("Search index ready: %s", stats)
            return store
        except Exception:
            logger.exception("Search index could not be built; search is off")
            return None

    def get_agent(self) -> Agent:
        if self.folder is None:
            raise no_documents_loaded()
        if self.readable_count == 0:
            raise no_documents_loaded("None of the files in this folder could be read.")
        self.get_llm()
        if self.agent is None:
            self.agent = Agent(
                self.llm, self.folder.documents, self.vector_store, self.router, self.settings.scope_mode
            )
        return self.agent

    def get_llm(self) -> LLMClient:
        """Made on first use, so a missing key never blocks loading files. Raises AIUnavailableError."""
        if self.llm is None:
            settings = self.settings
            self.llm = LLMClient(
                settings.groq_api_key, settings.model, settings.fallback_model, usage=self.usage,
                gemini_api_key=settings.gemini_api_key, gemini_model=settings.gemini_model,
                gemini_daily_requests=settings.gemini_daily_requests,
            )  # fmt: skip
            self.router = make_router(settings, self.usage)
        return self.llm

    def models_status(self, refresh: bool = False) -> list[dict]:
        """The models the user can pick, with what is left of their free limits."""
        llm = self.get_llm()
        if refresh and not self._chat_lock.locked():  # a question in progress already updates the numbers
            for model in llm.configured_models:
                llm.check(model)
        return [self.usage.snapshot(model) for model in llm.configured_models]

    def ask(
        self, question: str, history: list[dict], ui_language: str | None = None, should_stop=None,
        model: str | None = None,
    ) -> AgentAnswer:  # fmt: skip
        agent = self.get_agent()
        with self._chat_lock:
            self.llm.prefer(model)
            return agent.ask(question, history, ui_language, should_stop)

    def load_on_start(self) -> None:
        """Load DOCS_FOLDER from .env in the background, so the server starts at once."""
        folder = self.settings.docs_folder
        if not folder or not Path(folder).is_dir():
            return

        def run() -> None:
            try:
                self.load(folder)
            except Exception:
                logger.exception("Could not load DOCS_FOLDER %s", folder)

        self.loading_folder = folder  # set now, so a Client that opens right away already sees "loading"
        threading.Thread(target=run, daemon=True).start()
