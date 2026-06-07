"""Database client: persist papers and their embedded chunks to Postgres/pgvector.

Hand-rolled async SQL over ``asyncpg`` with parameterized queries only. A lazily-built
connection pool registers the pgvector codec (so ``list[float]`` maps to ``vector``) and a
jsonb codec (so author lists serialize directly). Writes go through the table-owner role,
which bypasses RLS; the schema itself lives in ``supabase/migrations/``.
"""

import json
from datetime import date, datetime

import asyncpg
from pgvector.asyncpg import register_vector
from pydantic import BaseModel

from arxiv_digest.clients.arxiv import Author, Paper, Summary
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
_DELETE_CHUNKS_SQL = "delete from paper_chunks where arxiv_id = $1"
_INSERT_CHUNK_SQL = (
    "insert into paper_chunks (arxiv_id, chunk_index, content, embedding) values ($1, $2, $3, $4)"
)
_SELECT_ACTIVE_SUBSCRIBERS_SQL = "select email, interests from subscribers where is_active = true"

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

# --- Read queries (the API's thin handlers call these) ---
# Paper columns the API serves, in PaperOut field order. `full_text` is appended only for the
# single-paper read (it is large; list/week responses omit it to keep payloads small).
_PAPER_SELECT_COLUMNS = (
    "arxiv_id, entry_id, title, abstract, authors, primary_category, categories, "
    "comment, journal_ref, doi, published, updated, pdf_url, topics, "
    "classification_rationale, summary_short, summary_long, summary_conclusions"
)
_GET_PAPER_SQL = f"select {_PAPER_SELECT_COLUMNS}, full_text from papers where arxiv_id = $1"  # noqa: S608
_TOPIC_COUNTS_SQL = (
    "select topic, count(*) as count from papers, unnest(topics) as topic group by topic"
)
_CATEGORIES_SQL = "select distinct unnest(categories) as category from papers order by category"

# A weekly "issue" is not stored — it is derived by the ISO week (Mon-Sun) of `published`,
# mirroring frontend/src/data/week.ts. These fragments name the derived columns; `date_trunc`
# returns the week's Monday, so it groups the week and yields its start/end/label/key.
_WEEK_KEY_EXPR = "to_char(date_trunc('week', published), 'IYYY\"-W\"IW')"
_WEEK_SUMMARY_SELECT = (
    "'Week of ' || to_char(date_trunc('week', published), 'FMMon FMDD, YYYY') as label, "
    "count(*) as count, "
    "date_trunc('week', published)::date as start, "
    "(date_trunc('week', published) + interval '6 days')::date as \"end\""
)
_LIST_WEEK_SUMMARIES_SQL = (
    f"select {_WEEK_KEY_EXPR} as week_key, {_WEEK_SUMMARY_SELECT} "  # noqa: S608
    "from papers group by date_trunc('week', published) "
    "order by date_trunc('week', published) desc"
)
_WEEK_SUMMARY_BY_KEY_SQL = (
    f"select $1 as week_key, {_WEEK_SUMMARY_SELECT} "  # noqa: S608
    f"from papers where {_WEEK_KEY_EXPR} = $1 group by date_trunc('week', published)"
)
_WEEK_PAPERS_SQL = (
    f"select {_PAPER_SELECT_COLUMNS} from papers "  # noqa: S608
    f"where {_WEEK_KEY_EXPR} = $1 order by published desc"
)
_LATEST_WEEK_KEY_SQL = (
    "select to_char(date_trunc('week', max(published)), 'IYYY\"-W\"IW') as week_key from papers"
)

_pool: asyncpg.Pool | None = None


class Subscriber(BaseModel):
    """A digest recipient. ``interests`` are categorization topic titles; empty means all topics."""

    email: str
    interests: list[str]


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


class WeekSummary(BaseModel):
    """One weekly issue's header — derived from the ISO week of its papers' ``published`` dates."""

    week_key: str
    label: str
    count: int
    start: date
    end: date


class WeekIssue(BaseModel):
    """A weekly issue: its summary plus the papers published that ISO week, newest first."""

    week: WeekSummary
    papers: list[Paper]


class DBError(RuntimeError):
    """Raised when the database is unconfigured or a write fails."""


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Register pgvector + jsonb codecs so vectors and author lists pass through natively."""
    await register_vector(conn)
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


async def store_papers(
    papers: list[Paper], chunks: dict[str, list[tuple[str, list[float]]]]
) -> None:
    """Upsert each paper and replace its chunks, one transaction per paper (idempotent)."""
    if not papers:
        return
    pool = await _get_pool()
    async with pool.acquire() as conn:
        for paper in papers:
            paper_chunks = chunks.get(paper.arxiv_id, [])
            chunk_rows = [
                (paper.arxiv_id, index, content, embedding)
                for index, (content, embedding) in enumerate(paper_chunks)
            ]
            try:
                async with conn.transaction():
                    await conn.execute(_UPSERT_PAPER_SQL, *_paper_values(paper))
                    await conn.execute(_DELETE_CHUNKS_SQL, paper.arxiv_id)
                    await conn.executemany(_INSERT_CHUNK_SQL, chunk_rows)
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
    return [Subscriber(email=row["email"], interests=list(row["interests"])) for row in rows]


# --- Read functions for the API (parameterized; return domain objects) ---


def _summary_from_row(row: asyncpg.Record) -> Summary | None:
    """Reassemble a paper's ``Summary`` from its three columns; ``None`` if it has none."""
    # The three summary columns are written together, so a null `short` means no summary at all.
    if row["summary_short"] is None:
        return None
    return Summary(
        short=row["summary_short"],
        long=row["summary_long"],
        conclusions=row["summary_conclusions"],
    )


def _row_to_paper(row: asyncpg.Record, *, include_full_text: bool) -> Paper:
    """Build a ``Paper`` from a DB row. ``full_text`` is read only when the row carries it."""
    return Paper(
        arxiv_id=row["arxiv_id"],
        entry_id=row["entry_id"],
        title=row["title"],
        abstract=row["abstract"],
        authors=[Author(**author) for author in row["authors"]],
        primary_category=row["primary_category"],
        categories=list(row["categories"]),
        comment=row["comment"],
        journal_ref=row["journal_ref"],
        doi=row["doi"],
        published=row["published"],
        updated=row["updated"],
        pdf_url=row["pdf_url"],
        full_text=row["full_text"] if include_full_text else None,
        topics=list(row["topics"]),
        summary=_summary_from_row(row),
        classification_rationale=row["classification_rationale"],
    )


def _build_list_papers_query(
    topics: list[str] | None,
    categories: list[str] | None,
    date_from: str | None,
    date_to: str | None,
    q: str | None,
) -> tuple[str, list[object]]:
    """Build the parameterized ``list_papers`` SQL and its bind args from optional filters.

    Filters AND together; each appends its value to ``args`` and references it by position.
    Topic/category use array overlap (``&&``); ``q`` is a case-insensitive substring over
    title, abstract and the authors JSON. Dates are inclusive ``YYYY-MM-DD`` bounds.
    """
    conditions: list[str] = []
    args: list[object] = []
    if topics:
        args.append(topics)
        conditions.append(f"topics && ${len(args)}::text[]")
    if categories:
        args.append(categories)
        conditions.append(f"categories && ${len(args)}::text[]")
    if date_from:
        # asyncpg binds a `::date` placeholder as a date type, so pass a date, not a string.
        args.append(date.fromisoformat(date_from))
        conditions.append(f"published >= ${len(args)}::date")
    if date_to:
        args.append(date.fromisoformat(date_to))
        conditions.append(f"published < ${len(args)}::date + 1")
    if q:
        args.append(f"%{q}%")
        placeholder = f"${len(args)}"
        conditions.append(
            f"(title ilike {placeholder} or abstract ilike {placeholder} "
            f"or authors::text ilike {placeholder})"
        )
    where = f" where {' and '.join(conditions)}" if conditions else ""
    # S608: only the fixed column list and $-placeholder fragments are interpolated; every
    # user value is bound through `args`.
    sql = f"select {_PAPER_SELECT_COLUMNS} from papers{where} order by published desc"  # noqa: S608
    return sql, args


async def list_papers(
    *,
    topics: list[str] | None = None,
    categories: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    q: str | None = None,
) -> list[Paper]:
    """Return papers matching the given filters, newest first (without full text)."""
    sql, args = _build_list_papers_query(topics, categories, date_from, date_to, q)
    pool = await _get_pool()
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *args)
    except asyncpg.PostgresError as exc:
        msg = f"failed to list papers: {exc}"
        raise DBError(msg) from exc
    return [_row_to_paper(row, include_full_text=False) for row in rows]


async def get_paper(arxiv_id: str) -> Paper | None:
    """Return one paper (with full text) by arXiv id, or ``None`` if it is not stored."""
    pool = await _get_pool()
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(_GET_PAPER_SQL, arxiv_id)
    except asyncpg.PostgresError as exc:
        msg = f"failed to get paper {arxiv_id}: {exc}"
        raise DBError(msg) from exc
    return _row_to_paper(row, include_full_text=True) if row else None


async def list_topic_counts() -> dict[str, int]:
    """Return a topic-title -> paper-count map over the ``topics`` array.

    Taxonomy ordering and zero-count omission are applied by the caller (the ``/topics`` route).
    """
    pool = await _get_pool()
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(_TOPIC_COUNTS_SQL)
    except asyncpg.PostgresError as exc:
        msg = f"failed to count topics: {exc}"
        raise DBError(msg) from exc
    return {row["topic"]: row["count"] for row in rows}


async def list_categories() -> list[str]:
    """Return the distinct arXiv category codes present across all papers, sorted."""
    pool = await _get_pool()
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(_CATEGORIES_SQL)
    except asyncpg.PostgresError as exc:
        msg = f"failed to list categories: {exc}"
        raise DBError(msg) from exc
    return [row["category"] for row in rows]


def _row_to_week_summary(row: asyncpg.Record) -> WeekSummary:
    """Build a ``WeekSummary`` from a row carrying the derived week columns."""
    return WeekSummary(
        week_key=row["week_key"],
        label=row["label"],
        count=row["count"],
        start=row["start"],
        end=row["end"],
    )


async def list_week_summaries() -> list[WeekSummary]:
    """Return one summary per ISO week that has papers, newest week first."""
    pool = await _get_pool()
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(_LIST_WEEK_SUMMARIES_SQL)
    except asyncpg.PostgresError as exc:
        msg = f"failed to list week summaries: {exc}"
        raise DBError(msg) from exc
    return [_row_to_week_summary(row) for row in rows]


async def get_week(week_key: str) -> WeekIssue | None:
    """Return the issue for an ISO week (e.g. ``"2026-W23"``), or ``None`` if it has no papers."""
    pool = await _get_pool()
    try:
        async with pool.acquire() as conn:
            summary_row = await conn.fetchrow(_WEEK_SUMMARY_BY_KEY_SQL, week_key)
            if summary_row is None:
                return None
            paper_rows = await conn.fetch(_WEEK_PAPERS_SQL, week_key)
    except asyncpg.PostgresError as exc:
        msg = f"failed to get week {week_key}: {exc}"
        raise DBError(msg) from exc
    papers = [_row_to_paper(row, include_full_text=False) for row in paper_rows]
    return WeekIssue(week=_row_to_week_summary(summary_row), papers=papers)


async def get_latest_week() -> WeekIssue | None:
    """Return the most recent ISO week's issue, or ``None`` if no papers are stored."""
    pool = await _get_pool()
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(_LATEST_WEEK_KEY_SQL)
    except asyncpg.PostgresError as exc:
        msg = f"failed to find the latest week: {exc}"
        raise DBError(msg) from exc
    week_key = row["week_key"] if row else None
    if week_key is None:
        return None
    return await get_week(week_key)
