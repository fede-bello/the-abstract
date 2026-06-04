"""Classification logic: keep useful papers, drop noise."""

from arxiv_digest.clients.arxiv import Paper


async def classify_papers(papers: list[Paper]) -> list[Paper]:
    """Return only the papers worth processing.

    TODO: send each paper's metadata (title, abstract, authors, affiliations,
    comment) to the LLM and keep the ones labelled "useful". Pass-through for now.
    """
    return papers
