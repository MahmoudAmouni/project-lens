"""All settings from .env, read in one place."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OPENROUTER_MODELS = "nvidia/nemotron-3-ultra-550b-a55b:free,minimax/minimax-m3.1-flash:free"


def project_path(value: str) -> str:
    """Relative paths in .env are relative to the project folder, not to where the command runs."""
    path = Path(value).expanduser()
    return str(path if path.is_absolute() else (PROJECT_ROOT / path).resolve())


@dataclass(frozen=True)
class Settings:
    groq_api_key: str
    model: str
    fallback_model: str
    router_model: str  # small fast model(s) that read the question first: "model,backup"
    gemini_api_key: str  # optional: adds Google Gemini as one more choice in the model picker
    gemini_model: str
    gemini_daily_requests: int  # Google's free daily request limit per model; corrected by its limit errors
    openrouter_api_key: str  # optional: adds OpenRouter's free models (names end with ":free") as more choices
    openrouter_model: str
    scope_mode: str  # "strict": only questions about the documents; "relaxed": off-topic goes to the agent too
    docs_folder: str
    max_file_mb: float
    chroma_dir: str
    usage_file: str  # token use per model, so "tokens left today" survives a restart


def load_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")
    docs_folder = os.getenv("DOCS_FOLDER", "").strip()
    return Settings(
        groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
        model=os.getenv("MODEL", "openai/gpt-oss-120b").strip(),
        fallback_model=os.getenv("FALLBACK_MODEL", "openai/gpt-oss-20b,qwen/qwen3.8-27b").strip(),
        router_model=os.getenv("ROUTER_MODEL", "openai/gpt-oss-20b,qwen/qwen3.8-27b").strip(),
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash,gemini-3.5-flash-lite").strip(),
        gemini_daily_requests=int(os.getenv("GEMINI_DAILY_REQUESTS", "20")),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", "").strip(),
        openrouter_model=os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODELS).strip(),
        scope_mode=os.getenv("SCOPE_MODE", "strict").strip().lower(),
        docs_folder=project_path(docs_folder) if docs_folder else "",
        max_file_mb=float(os.getenv("MAX_FILE_MB", "100")),
        chroma_dir=project_path(os.getenv("CHROMA_DIR", "./.chroma")),
        usage_file=project_path(os.getenv("USAGE_FILE", "./.usage/token_usage.json")),
    )
