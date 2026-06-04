"""Summarization step (stub): generate short and long summaries for each paper."""

from workflows import step

from arxiv_digest.steps.categorization.events import CategorizedEvent
from arxiv_digest.steps.summarization.events import SummarizedEvent
from arxiv_digest.workflows.digest import DigestWorkflow


@step(workflow=DigestWorkflow)
async def summarize(ev: CategorizedEvent) -> SummarizedEvent:
    """Pass papers through unchanged for now.

    TODO: generate a short (3-4 bullet) and long (~2 paragraph) summary plus a
    conclusions section for each paper from its parsed content.
    """
    return SummarizedEvent(papers=ev.papers)
