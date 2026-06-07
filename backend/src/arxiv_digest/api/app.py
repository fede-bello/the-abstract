"""FastAPI application — the read-only HTTP layer the web frontend talks to.

Thin by design: every handler delegates to ``clients/db.py``. Run it with
``uv run arxiv-digest serve`` (or ``uvicorn arxiv_digest.api.app:app``).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from arxiv_digest.api.routers import ask, meta, papers, weeks
from arxiv_digest.clients.db import close_pool
from arxiv_digest.config import settings


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Close the shared DB connection pool on shutdown."""
    yield
    await close_pool()


app = FastAPI(title="arXiv ML Digest API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(papers.router)
app.include_router(weeks.router)
app.include_router(meta.router)
app.include_router(ask.router)
