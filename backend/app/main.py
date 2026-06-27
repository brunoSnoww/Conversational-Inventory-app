from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.config import get_settings
from app.db.pool import close_pool, get_pool
from app.inventory.router import router as inventory_router
from app.sync.router import router as sync_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    get_pool()
    yield
    close_pool()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Inventory API",
        description="Conversational inventory management (FastAPI + PowerSync upload connector)",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*", "x-user-agent"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth_router, prefix="/api")
    app.include_router(sync_router, prefix="/api")
    app.include_router(inventory_router, prefix="/api")
    return app


app = create_app()
