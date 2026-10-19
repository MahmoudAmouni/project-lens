"""POST /api/chat: ask a question about the loaded documents."""

from fastapi import APIRouter, Request

from Server.schemas.chat_schemas import ChatRequest, ChatResponse
from Server.state import AppState

router = APIRouter(tags=["chat"])


@router.post("/chat")
def chat(body: ChatRequest, request: Request) -> ChatResponse:
    """The agent answers from the documents, with sources and the steps it took."""
    state: AppState = request.app.state.lens
    history = [message.model_dump() for message in body.history]
    answer = state.ask(body.question.strip(), history)
    return ChatResponse(
        answer=answer.answer,
        table=answer.table,
        sources=answer.sources,
        steps=answer.steps,
        model=answer.model,
    )
