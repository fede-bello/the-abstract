"""Storage logic: chunk + embed each paper's text and persist it to Postgres/pgvector.

Splits the parsed ``full_text`` into chunks (for RAG retrieval), embeds each chunk with the
local model, and writes the paper row plus its chunk embeddings via the DB client. External
I/O lives in the clients; this orchestrates them.
"""

from llama_index.core.node_parser import SentenceSplitter

from arxiv_digest.clients.arxiv import Paper
from arxiv_digest.clients.db import store_papers as db_store_papers
from arxiv_digest.clients.embed import embed_texts
from arxiv_digest.config import settings


def _chunk_paper(paper: Paper) -> list[str]:
    """Split a paper's parsed text into retrieval chunks (empty if it has no text)."""
    if not paper.full_text:
        return []
    splitter = SentenceSplitter(
        chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap
    )
    return splitter.split_text(paper.full_text)


async def store_papers(papers: list[Paper]) -> list[Paper]:
    """Persist metadata, summaries, and chunk embeddings for each paper."""
    chunks: dict[str, list[tuple[str, list[float]]]] = {}
    for paper in papers:
        texts = _chunk_paper(paper)
        vectors = await embed_texts(texts)
        chunks[paper.arxiv_id] = list(zip(texts, vectors, strict=True))
    await db_store_papers(papers, chunks)
    return papers
