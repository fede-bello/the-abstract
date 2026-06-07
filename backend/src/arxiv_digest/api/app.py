"""FastAPI application — the server-side endpoints the web frontend calls.

The SPA reads papers/weeks/facets straight from Supabase via the anon key, so the only endpoint
here is ``/ask`` — a placeholder today, the seed for RAG-backed Q&A (which needs server-side LLM
keys). Run it with ``uv run arxiv-digest serve`` (or ``uvicorn arxiv_digest.api.app:app``).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from arxiv_digest.api.routers import ask
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

app.include_router(ask.router)
