"""GET /api/models: the AI models the user can pick, with how much of their free Groq limit is left."""

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from Server.state import AppState

router = APIRouter(tags=["models"])


@router.get("/models")
async def models(request: Request, refresh: bool = False) -> dict:
    """`refresh=true` asks Groq for fresh numbers (one tiny call per model)."""
    state: AppState = request.app.state.lens
    return {"models": await run_in_threadpool(state.models_status, refresh)}
