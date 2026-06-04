"""Categorization logic: assign multi-label topic tags to each paper."""

from arxiv_digest.clients.arxiv import Paper


async def categorize_papers(papers: list[Paper]) -> list[Paper]:
    """Tag each paper with one or more topics from the predefined category list.

    TODO: classify into LLMs, Diffusion, RL, Agents, ... from abstract + content.
    Pass-through for now.
    """
    return papers
