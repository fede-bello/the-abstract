"""Summarization logic: generate short and long summaries for each paper."""

from arxiv_digest.clients.arxiv import Paper


async def summarize_papers(papers: list[Paper]) -> list[Paper]:
    """Produce a short (3-4 bullet) and long (~2 paragraph) summary per paper.

    TODO: summarize each paper from its parsed content, with a conclusions section.
    Pass-through for now.
    """
    return papers
