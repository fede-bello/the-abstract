"""Integration test for the DB client — needs a real Supabase Postgres with the migration applied.

Skips cleanly when SUPABASE_DB_URL is unset, so the default suite stays green.
"""

import asyncpg
import pytest
from _builders import make_paper

from arxiv_digest.clients.db import store_papers
from arxiv_digest.config import settings

_TEST_ARXIV_ID = "test.0000001"


@pytest.mark.integration
async def test_store_papers_writes_paper_and_chunks():
    dsn = settings.supabase_db_url.get_secret_value()
    if not dsn:
        pytest.skip("SUPABASE_DB_URL not set")

    paper = make_paper(arxiv_id=_TEST_ARXIV_ID, full_text="body")
    chunks = {_TEST_ARXIV_ID: [("a chunk", [0.1] * settings.embedding_dim)]}

    try:
        await store_papers([paper], chunks)
        conn = await asyncpg.connect(dsn=dsn)
        try:
            n_papers = await conn.fetchval(
                "select count(*) from papers where arxiv_id = $1", _TEST_ARXIV_ID
            )
            n_chunks = await conn.fetchval(
                "select count(*) from paper_chunks where arxiv_id = $1", _TEST_ARXIV_ID
            )
        finally:
            await conn.close()
        assert n_papers == 1
        assert n_chunks == 1
    finally:
        conn = await asyncpg.connect(dsn=dsn)
        await conn.execute("delete from papers where arxiv_id = $1", _TEST_ARXIV_ID)
        await conn.close()
