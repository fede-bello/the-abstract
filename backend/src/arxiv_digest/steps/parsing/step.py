"""Parsing logic: fully parse each useful paper's PDF."""

from arxiv_digest.clients.arxiv import Paper


async def parse_papers(papers: list[Paper]) -> list[Paper]:
    """Parse each paper's PDF into text, figures, and tables.

    TODO: run each ``pdf_path`` through LlamaParse and attach the parsed content.
    Pass-through for now.
    """
    return papers
