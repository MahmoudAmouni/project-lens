"""POST /api/chat: ask a question about the loaded documents. Stops when the browser hangs up (Stop button)."""

import asyncio
import threading

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from Server.schemas.chat_schemas import ChatRequest, ChatResponse
from Server.state import AppState

router = APIRouter(tags=["chat"])
DISCONNECT_CHECK_SECONDS = 0.5


@router.post("/chat")
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    """The agent answers from the documents, with sources and the steps it took."""
    state: AppState = request.app.state.lens
    history = [message.model_dump() for message in body.history]
    stopped = threading.Event()
    work = asyncio.ensure_future(
        run_in_threadpool(state.ask, body.question.strip(), history, body.ui_language, stopped.is_set)
    )
    while not work.done():  # the agent runs in a worker thread; meanwhile, watch for the user pressing Stop
        await asyncio.wait({work}, timeout=DISCONNECT_CHECK_SECONDS)
        if not work.done() and await request.is_disconnected():
            stopped.set()  # the agent ends at its next check (no more Groq calls)
    answer = work.result()
    return ChatResponse(
        answer=answer.answer,
        table=answer.table,
        sources=answer.sources,
        steps=answer.steps,
        model=answer.model,
        kind=answer.kind,
        style=answer.style,
        suggestions=answer.suggestions,
    )
