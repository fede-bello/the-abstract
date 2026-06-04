"""Classification step (stub): label each paper as useful vs noise from its metadata."""

from workflows import step

from arxiv_digest.steps.classification.events import ClassifiedEvent
from arxiv_digest.steps.ingestion.events import PapersFetchedEvent
from arxiv_digest.workflows.digest import DigestWorkflow


@step(workflow=DigestWorkflow)
async def classify(ev: PapersFetchedEvent) -> ClassifiedEvent:
    """Pass papers through unchanged for now.

    TODO: send each paper's metadata (title, abstract, authors, affiliations,
    comment) to the LLM and keep only the papers labelled "useful".
    """
    return ClassifiedEvent(papers=ev.papers)
