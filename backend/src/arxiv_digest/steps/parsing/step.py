"""Parsing step (stub): fully parse each useful paper's PDF."""

from workflows import step

from arxiv_digest.steps.classification.events import ClassifiedEvent
from arxiv_digest.steps.parsing.events import ParsedEvent
from arxiv_digest.workflows.digest import DigestWorkflow


@step(workflow=DigestWorkflow)
async def parse(ev: ClassifiedEvent) -> ParsedEvent:
    """Pass papers through unchanged for now.

    TODO: parse each paper's PDF (`pdf_path`) with LlamaParse into text, figures,
    and tables, and attach the parsed content to the paper.
    """
    return ParsedEvent(papers=ev.papers)
