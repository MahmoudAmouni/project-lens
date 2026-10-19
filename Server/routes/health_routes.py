"""GET /api/health: is the server up, which model, how many documents."""

from fastapi import APIRouter, Request

from Server.state import AppState

router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request) -> dict:
    state: AppState = request.app.state.lens
    return {
        "status": "ok",
        "model": state.settings.model,
        "ai_key_set": bool(state.settings.groq_api_key),
        "documents_loaded": state.readable_count,
        "loading": state.loading_folder is not None,
        "loading_step": state.loading_step,
    }
