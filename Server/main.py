"""Creates the FastAPI app: settings, CORS, error handlers and routes.

Run: uvicorn Server.main:app --reload --port 8000   (API docs at http://localhost:8000/docs)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from Server.config import load_settings
from Server.errors import add_error_handlers
from Server.routes import chat_routes, document_routes, health_routes, model_routes
from Server.state import AppState

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
CLIENT_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def create_app(load_docs_folder: bool = True) -> FastAPI:
    state = AppState(load_settings())

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if load_docs_folder:
            state.load_on_start()
        yield

    app = FastAPI(title="ProjectLens API", version="0.1.0", lifespan=lifespan)
    app.state.lens = state
    app.add_middleware(CORSMiddleware, allow_origins=CLIENT_ORIGINS, allow_methods=["*"], allow_headers=["*"])
    add_error_handlers(app)
    for routes in (health_routes, document_routes, chat_routes, model_routes):
        app.include_router(routes.router, prefix="/api")
    return app


app = create_app()
