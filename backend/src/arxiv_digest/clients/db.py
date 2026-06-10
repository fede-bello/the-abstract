"""Database client: persist papers to Postgres.

Hand-rolled async SQL over ``asyncpg`` with parameterized queries only. A lazily-built
connection pool registers a jsonb codec (so author lists serialize directly). Writes go
through the table-owner role, which bypasses RLS; the schema itself lives in
``supabase/migrations/``.
"""

import json
from datetime import datetime

import asyncpg
from pydantic import BaseModel

from arxiv_digest.clients.arxiv import Paper
from arxiv_digest.config import settings

# Columns written on upsert, in value order. ``arxiv_id`` is the conflict key; the rest are
# overwritten on re-runs. ``classification_label`` is left to its DB default ('useful').
_PAPER_COLUMNS = (
    "arxiv_id",
    "entry_id",
    "title",
    "abstract",
    "authors",
    "primary_category",
    "categories",
    "comment",
    "journal_ref",
    "doi",
    "published",
    "updated",
    "pdf_url",
    "full_text",
    "topics",
    "classification_rationale",
    "summary_short",
    "summary_long",
    "summary_conclusions",
)
_PLACEHOLDERS = ", ".join(f"${i}" for i in range(1, len(_PAPER_COLUMNS) + 1))
_UPDATE_SET = ", ".join(f"{c} = excluded.{c}" for c in _PAPER_COLUMNS if c != "arxiv_id")
_UPSERT_PAPER_SQL = (
    # S608: interpolates only the fixed _PAPER_COLUMNS constant — no user input.
    f"insert into papers ({', '.join(_PAPER_COLUMNS)}) values ({_PLACEHOLDERS}) "  # noqa: S608
    f"on conflict (arxiv_id) do update set {_UPDATE_SET}"
)
_SELECT_ACTIVE_SUBSCRIBERS_SQL = (
    "select email, interests, unsubscribe_token from subscribers where is_active = true"
)

_USAGE_COLUMNS = (
    "kind",
    "stage",
    "model",
    "input_tokens",
    "output_tokens",
    "pages",
    "tier",
    "cost_usd",
)
_USAGE_PLACEHOLDERS = ", ".join(f"${i}" for i in range(1, len(_USAGE_COLUMNS) + 1))
_INSERT_USAGE_SQL = (
    # S608: interpolates only the fixed _USAGE_COLUMNS constant — no user input.
    f"insert into usage_events ({', '.join(_USAGE_COLUMNS)}) values ({_USAGE_PLACEHOLDERS})"  # noqa: S608
)
_SELECT_WEEKLY_USAGE_SQL = (
    # Re-state `order by` here: the view's own ordering isn't guaranteed to survive an outer LIMIT.
    "select week, llm_calls, input_tokens, output_tokens, parse_jobs, parse_pages, "
    "llm_cost_usd, parse_cost_usd, total_cost_usd from weekly_usage order by week desc limit $1"
)

_pool: asyncpg.Pool | None = None


class Subscriber(BaseModel):
    """A digest recipient. ``interests`` are categorization topic titles; empty means all topics."""

    email: str
    interests: list[str]
    unsubscribe_token: str  # used to build the one-click unsubscribe link in each digest


class UsageEvent(BaseModel):
    """One paid external call to bill against the week.

    ``kind`` is 'llm' or 'parse'; the token/page/tier fields are populated only for the
    relevant kind.
    """

    kind: str
    stage: str | None = None
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    pages: int | None = None
    tier: str | None = None
    cost_usd: float = 0.0


class WeeklyUsage(BaseModel):
    """A single week's usage roll-up from the ``weekly_usage`` view."""

    week: datetime
    llm_calls: int
    input_tokens: int
    output_tokens: int
    parse_jobs: int
    parse_pages: int
    llm_cost_usd: float
    parse_cost_usd: float
    total_cost_usd: float


class DBError(RuntimeError):
    """Raised when the database is unconfigured or a write fails."""


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Register the jsonb codec so author lists pass through natively."""
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")


async def _get_pool() -> asyncpg.Pool:
    """Build (once) and return the asyncpg pool from the configured connection string."""
    global _pool  # noqa: PLW0603 — module-level singleton for the connection pool
    if _pool is None:
        dsn = settings.supabase_db_url.get_secret_value()
        if not dsn:
            msg = "SUPABASE_DB_URL is not set"
            raise DBError(msg)
        _pool = await asyncpg.create_pool(dsn=dsn, init=_init_connection)
    return _pool


async def close_pool() -> None:
    """Close the shared connection pool if one is open. A no-op otherwise; safe to call twice."""
    global _pool  # noqa: PLW0603 — module-level singleton for the connection pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def _paper_values(paper: Paper) -> tuple[object, ...]:
    """Flatten a paper into the upsert value tuple, in ``_PAPER_COLUMNS`` order."""
    summary = paper.summary
    return (
        paper.arxiv_id,
        paper.entry_id,
        paper.title,
        paper.abstract,
        [author.model_dump() for author in paper.authors],
        paper.primary_category,
        paper.categories,
        paper.comment,
        paper.journal_ref,
        paper.doi,
        paper.published,
        paper.updated,
        paper.pdf_url,
        paper.full_text,
        paper.topics,
        paper.classification_rationale,
        summary.short if summary else None,
        summary.long if summary else None,
        summary.conclusions if summary else None,
    )


async def store_papers(papers: list[Paper]) -> None:
    """Upsert each paper, one transaction per paper (idempotent)."""
    if not papers:
        return
    pool = await _get_pool()
    async with pool.acquire() as conn:
        for paper in papers:
            try:
                async with conn.transaction():
                    await conn.execute(_UPSERT_PAPER_SQL, *_paper_values(paper))
            except asyncpg.PostgresError as exc:
                msg = f"failed to store {paper.arxiv_id}: {exc}"
                raise DBError(msg) from exc


async def record_usage_event(event: UsageEvent) -> None:
    """Insert one usage row. Raises ``DBError`` on failure; callers record best-effort."""
    pool = await _get_pool()
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                _INSERT_USAGE_SQL,
                event.kind,
                event.stage,
                event.model,
                event.input_tokens,
                event.output_tokens,
                event.pages,
                event.tier,
                event.cost_usd,
            )
    except asyncpg.PostgresError as exc:
        msg = f"failed to record usage event: {exc}"
        raise DBError(msg) from exc


async def fetch_weekly_usage(weeks: int) -> list[WeeklyUsage]:
    """Return the most recent ``weeks`` weekly usage roll-ups, newest first."""
    pool = await _get_pool()
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(_SELECT_WEEKLY_USAGE_SQL, weeks)
    except asyncpg.PostgresError as exc:
        msg = f"failed to read weekly usage: {exc}"
        raise DBError(msg) from exc
    return [
        WeeklyUsage(
            week=row["week"],
            llm_calls=row["llm_calls"],
            input_tokens=row["input_tokens"],
            output_tokens=row["output_tokens"],
            parse_jobs=row["parse_jobs"],
            parse_pages=row["parse_pages"],
            llm_cost_usd=float(row["llm_cost_usd"]),
            parse_cost_usd=float(row["parse_cost_usd"]),
            total_cost_usd=float(row["total_cost_usd"]),
        )
        for row in rows
    ]


async def get_active_subscribers() -> list[Subscriber]:
    """Return every active digest recipient with their topic interests."""
    pool = await _get_pool()
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(_SELECT_ACTIVE_SUBSCRIBERS_SQL)
    except asyncpg.PostgresError as exc:
        msg = f"failed to read subscribers: {exc}"
        raise DBError(msg) from exc
    return [
        Subscriber(
            email=row["email"],
            interests=list(row["interests"]),
            unsubscribe_token=str(row["unsubscribe_token"]),
        )
        for row in rows
    ]
