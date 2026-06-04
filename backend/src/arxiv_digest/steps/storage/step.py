"""Storage logic: persist papers and their embeddings."""

from arxiv_digest.clients.arxiv import Paper


async def store_papers(papers: list[Paper]) -> list[Paper]:
    """Persist metadata, parsed content, summaries, and embeddings.

    TODO: write to Postgres/pgvector for retrieval and the Q&A app. Pass-through
    for now (returns the papers so distribution can use them).
    """
    return papers
