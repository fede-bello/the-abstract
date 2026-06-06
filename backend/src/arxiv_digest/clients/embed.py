"""Embedding client: encode text into vectors with a local HuggingFace model.

Uses ``BAAI/bge-small-en-v1.5`` (384-dim) by default — free, no API key, fine for the
weekly volume. The model is loaded once and reused; encoding is CPU/GPU-bound and sync,
so it runs in a worker thread to keep the event loop free. The output dimension must
match the ``vector(N)`` column in the DB migration (guarded against drift).
"""

import asyncio
from typing import TYPE_CHECKING

from arxiv_digest.config import settings

if TYPE_CHECKING:
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Heavy import (torch + sentence-transformers) is deferred to first use so callers that
# never embed don't pay its cost.
_model: "HuggingFaceEmbedding | None" = None


class EmbeddingError(RuntimeError):
    """Raised when the embedding model produces vectors of an unexpected dimension."""


def _get_model() -> "HuggingFaceEmbedding":
    """Build (once) and return the configured HuggingFace embedding model."""
    global _model  # noqa: PLW0603 — module-level singleton for the loaded model
    if _model is None:
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding

        _model = HuggingFaceEmbedding(
            model_name=settings.embedding_model,
            device=settings.embedding_device,
        )
    return _model


def _encode(texts: list[str]) -> list[list[float]]:
    """Synchronously embed a batch of texts, validating the vector dimension."""
    model = _get_model()
    vectors: list[list[float]] = model.get_text_embedding_batch(texts)
    for vector in vectors:
        if len(vector) != settings.embedding_dim:
            msg = f"expected {settings.embedding_dim}-dim embeddings, got {len(vector)}"
            raise EmbeddingError(msg)
    return vectors


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts into vectors, off the event loop."""
    if not texts:
        return []
    return await asyncio.to_thread(_encode, texts)
