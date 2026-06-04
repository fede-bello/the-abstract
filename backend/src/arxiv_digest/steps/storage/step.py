"""Storage step (stub): persist papers and their embeddings."""

from workflows import step

from arxiv_digest.steps.storage.events import StoredEvent
from arxiv_digest.steps.summarization.events import SummarizedEvent
from arxiv_digest.workflows.digest import DigestWorkflow


@step(workflow=DigestWorkflow)
async def store(ev: SummarizedEvent) -> StoredEvent:
    """Pass papers through unchanged for now.

    TODO: persist metadata, parsed content, summaries, and embeddings to
    Postgres/pgvector for retrieval and the Q&A app.
    """
    return StoredEvent(papers=ev.papers)
