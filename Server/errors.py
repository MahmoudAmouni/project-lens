"""One error shape for the whole API: {"error": {"code": ..., "message": ...}}."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from AI.errors import AIRateLimitedError, AIUnavailableError, QuestionStopped

logger = logging.getLogger("projectlens")


class ApiError(Exception):
    """An error with a code the Client understands."""

    def __init__(self, code: str, message: str, status: int):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def folder_not_found(message: str) -> ApiError:
    return ApiError("FOLDER_NOT_FOUND", message, 404)


def folder_empty(message: str) -> ApiError:
    return ApiError("FOLDER_EMPTY", message, 422)


def no_documents_loaded(message: str = "Load a folder with PDF, Excel or Word files first.") -> ApiError:
    return ApiError("NO_DOCUMENTS_LOADED", message, 409)


def error_response(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def add_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error(_: Request, error: ApiError) -> JSONResponse:
        return error_response(error.code, error.message, error.status)

    @app.exception_handler(AIUnavailableError)
    async def ai_unavailable(_: Request, error: AIUnavailableError) -> JSONResponse:
        return error_response("AI_UNAVAILABLE", str(error), 503)

    @app.exception_handler(AIRateLimitedError)
    async def ai_rate_limited(_: Request, error: AIRateLimitedError) -> JSONResponse:
        return error_response("AI_RATE_LIMITED", str(error), 429)

    @app.exception_handler(QuestionStopped)
    async def question_stopped(_: Request, error: QuestionStopped) -> JSONResponse:
        return error_response("STOPPED", "The question was stopped.", 499)  # 499: the client closed the request

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, error: RequestValidationError) -> JSONResponse:
        first = error.errors()[0] if error.errors() else {}
        field = ".".join(str(part) for part in first.get("loc", []) if part != "body")
        message = f"{field}: {first.get('msg', 'invalid value')}" if field else "The request is not valid."
        return error_response("INVALID_REQUEST", message, 422)

    @app.exception_handler(Exception)
    async def internal_error(_: Request, error: Exception) -> JSONResponse:
        logger.exception("Unexpected error", exc_info=error)
        return error_response("INTERNAL_ERROR", "Something went wrong on the server. Please try again.", 500)
