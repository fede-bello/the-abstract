"""Categorization step (stub): assign multi-label topic tags to each paper."""

from workflows import step

from arxiv_digest.steps.categorization.events import CategorizedEvent
from arxiv_digest.steps.parsing.events import ParsedEvent
from arxiv_digest.workflows.ingest import DigestWorkflow


@step(workflow=DigestWorkflow)
async def categorize(ev: ParsedEvent) -> CategorizedEvent:
    """Pass papers through unchanged for now.

    TODO: assign each paper one or more topic tags from the project's predefined
    category list (LLMs, Diffusion, RL, Agents, ...) using its abstract and content.
    """
    return CategorizedEvent(papers=ev.papers)
