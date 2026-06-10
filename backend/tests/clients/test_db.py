"""Integration test for the DB client — needs a real Supabase Postgres with the migration applied.

Skips cleanly when SUPABASE_DB_URL is unset, so the default suite stays green.
"""

import asyncpg
import pytest
from _builders import make_paper

from arxiv_digest.clients.db import (
    UsageEvent,
    close_pool,
    fetch_weekly_usage,
    get_active_subscribers,
    record_usage_event,
    store_papers,
)
from arxiv_digest.config import settings

_TEST_ARXIV_ID = "test.0000001"
_TEST_EMAIL = "test-subscriber@example.com"
_TEST_USAGE_SENTINEL = "__test_usage__"


@pytest.fixture(autouse=True)
async def _fresh_db_pool():
    """Reset the singleton pool after each test: it binds to one event loop, but pytest-asyncio
    gives each test its own loop, so a reused pool errors with 'another operation in progress'."""
    yield
    await close_pool()


@pytest.mark.integration
async def test_store_papers_writes_paper():
    dsn = settings.supabase_db_url.get_secret_value()
    if not dsn:
        pytest.skip("SUPABASE_DB_URL not set")

    paper = make_paper(arxiv_id=_TEST_ARXIV_ID, full_text="body")

    try:
        await store_papers([paper])
        conn = await asyncpg.connect(dsn=dsn)
        try:
            n_papers = await conn.fetchval(
                "select count(*) from papers where arxiv_id = $1", _TEST_ARXIV_ID
            )
        finally:
            await conn.close()
        assert n_papers == 1
    finally:
        conn = await asyncpg.connect(dsn=dsn)
        await conn.execute("delete from papers where arxiv_id = $1", _TEST_ARXIV_ID)
        await conn.close()


@pytest.mark.integration
async def test_record_usage_event_persists_the_row():
    dsn = settings.supabase_db_url.get_secret_value()
    if not dsn:
        pytest.skip("SUPABASE_DB_URL not set")

    try:
        await record_usage_event(
            UsageEvent(
                kind="llm",
                stage="classification",
                model=_TEST_USAGE_SENTINEL,
                input_tokens=11,
                output_tokens=22,
                cost_usd=0.001234,
            )
        )
        conn = await asyncpg.connect(dsn=dsn)
        try:
            row = await conn.fetchrow(
                "select kind, input_tokens, output_tokens, cost_usd "
                "from usage_events where model = $1",
                _TEST_USAGE_SENTINEL,
            )
        finally:
            await conn.close()
        assert row["kind"] == "llm"
        assert row["input_tokens"] == 11
        assert row["output_tokens"] == 22
        assert float(row["cost_usd"]) == pytest.approx(0.001234)
    finally:
        conn = await asyncpg.connect(dsn=dsn)
        await conn.execute("delete from usage_events where model = $1", _TEST_USAGE_SENTINEL)
        await conn.close()


@pytest.mark.integration
async def test_fetch_weekly_usage_aggregates_recorded_rows():
    dsn = settings.supabase_db_url.get_secret_value()
    if not dsn:
        pytest.skip("SUPABASE_DB_URL not set")

    try:
        await record_usage_event(
            UsageEvent(kind="llm", model=_TEST_USAGE_SENTINEL, input_tokens=5, cost_usd=0.01)
        )
        await record_usage_event(
            UsageEvent(kind="parse", tier=_TEST_USAGE_SENTINEL, pages=3, cost_usd=0.02)
        )
        weeks = await fetch_weekly_usage(8)
        assert weeks, "expected at least the current week"
        current = weeks[0]
        assert current.llm_calls >= 1
        assert current.parse_jobs >= 1
        assert current.total_cost_usd > 0.029  # our two rows add exactly 0.03; others only add
    finally:
        conn = await asyncpg.connect(dsn=dsn)
        await conn.execute(
            "delete from usage_events where model = $1 or tier = $1", _TEST_USAGE_SENTINEL
        )
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
