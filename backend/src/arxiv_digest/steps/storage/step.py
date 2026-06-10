"""Storage logic: persist each paper's metadata and summaries to Postgres.

Writes the paper rows via the DB client. External I/O lives in the clients; this
orchestrates them. (Chunk embeddings for RAG retrieval are not generated yet; the
paper_chunks table stays defined in the schema for when that returns.)
"""

from arxiv_digest.clients.arxiv import Paper
from arxiv_digest.clients.db import store_papers as db_store_papers


async def store_papers(papers: list[Paper]) -> list[Paper]:
    """Persist metadata and summaries for each paper."""
    await db_store_papers(papers)
    return papers
