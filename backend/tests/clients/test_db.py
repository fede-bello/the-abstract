"""Integration test for the DB client — needs a real Supabase Postgres with the migration applied.

Skips cleanly when SUPABASE_DB_URL is unset, so the default suite stays green.
"""

import asyncpg
import pytest
from _builders import make_paper

from arxiv_digest.clients.db import get_active_subscribers, store_papers
from arxiv_digest.config import settings

_TEST_ARXIV_ID = "test.0000001"
_TEST_EMAIL = "test-subscriber@example.com"


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


@pytest.mark.integration
async def test_get_active_subscribers_returns_active_rows():
    dsn = settings.supabase_db_url.get_secret_value()
    if not dsn:
        pytest.skip("SUPABASE_DB_URL not set")

    conn = await asyncpg.connect(dsn=dsn)
    try:
        await conn.execute("delete from subscribers where email = $1", _TEST_EMAIL)
        await conn.execute(
            "insert into subscribers (email, interests) values ($1, $2)", _TEST_EMAIL, ["LLMs"]
        )
    finally:
        await conn.close()

    try:
        subscribers = await get_active_subscribers()
        match = next((s for s in subscribers if s.email == _TEST_EMAIL), None)
        assert match is not None
        assert match.interests == ["LLMs"]
    finally:
        conn = await asyncpg.connect(dsn=dsn)
        await conn.execute("delete from subscribers where email = $1", _TEST_EMAIL)
        await conn.close()
