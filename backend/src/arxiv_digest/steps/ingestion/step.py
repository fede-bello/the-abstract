"""Ingestion step: pull recent ML papers from arXiv (metadata + PDFs)."""

from workflows import step
from workflows.events import StartEvent

from arxiv_digest.clients.arxiv import fetch_recent_papers
from arxiv_digest.config import settings
from arxiv_digest.steps.ingestion.events import PapersFetchedEvent
from arxiv_digest.workflows.ingest import DigestWorkflow


@step(workflow=DigestWorkflow)
async def fetch_papers(ev: StartEvent) -> PapersFetchedEvent:
    """Query arXiv for the most recent papers and download their PDFs.

    Categories, the result cap, and the look-back window come from settings, but can
    be overridden per run via ``workflow.run(max_results=5, days_back=7)``.
    """
    categories = ev.get("categories", settings.arxiv_categories)
    max_results = ev.get("max_results", settings.max_results)
    days_back = ev.get("days_back", settings.days_back)
    papers = await fetch_recent_papers(
        categories=categories,
        max_results=max_results,
        days_back=days_back,
        pdf_dir=settings.pdf_dir,
        max_attempts=settings.arxiv_max_attempts,
    )
    return PapersFetchedEvent(papers=papers)
