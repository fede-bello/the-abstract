"""Tests for the embedding client.

The dimension check loads the real local model (downloads on first run), so it's marked
`integration`. The empty-input guard is a pure unit test.
"""

import pytest

from arxiv_digest.clients.embed import embed_texts
from arxiv_digest.config import settings


async def test_embed_texts_empty_returns_empty():
    assert await embed_texts([]) == []


@pytest.mark.integration
async def test_embed_texts_returns_vectors_of_configured_dim():
    vectors = await embed_texts(["hello world", "a second sentence"])

    assert len(vectors) == 2
    assert all(len(v) == settings.embedding_dim for v in vectors)
