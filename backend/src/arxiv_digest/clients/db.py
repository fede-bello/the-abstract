"""Database client: persist papers and their embedded chunks to Postgres/pgvector.

Hand-rolled async SQL over ``asyncpg`` with parameterized queries only. A lazily-built
connection pool registers the pgvector codec (so ``list[float]`` maps to ``vector``) and a
jsonb codec (so author lists serialize directly). Writes go through the table-owner role,
which bypasses RLS; the schema itself lives in ``supabase/migrations/``.
"""

import json

import asyncpg
from pgvector.asyncpg import register_vector

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
_DELETE_CHUNKS_SQL = "delete from paper_chunks where arxiv_id = $1"
_INSERT_CHUNK_SQL = (
    "insert into paper_chunks (arxiv_id, chunk_index, content, embedding) values ($1, $2, $3, $4)"
)

_pool: asyncpg.Pool | None = None


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
