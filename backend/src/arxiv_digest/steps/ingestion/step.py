"""Ingestion logic: fetch recent ML papers from arXiv (metadata + PDFs)."""

from arxiv_digest.clients.arxiv import Paper, fetch_recent_papers
from arxiv_digest.config import settings


async def fetch_papers(max_results: int, days_back: int) -> list[Paper]:
    """Fetch recent arXiv papers across the configured ML categories."""
    return await fetch_recent_papers(
        categories=settings.arxiv_categories,
        max_results=max_results,
        days_back=days_back,
        pdf_dir=settings.pdf_dir,
        max_attempts=settings.arxiv_max_attempts,
    )
