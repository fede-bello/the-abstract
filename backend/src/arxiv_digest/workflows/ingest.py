"""The weekly arXiv ingestion pipeline.

This module is intentionally thin: it declares `DigestWorkflow` and registers each
pipeline stage. The stages themselves (their events and logic) live under
`arxiv_digest.steps`, one self-contained package per stage. The import block at the
bottom reads as the pipeline's table of contents — each import pulls in a step
module whose `@step(workflow=DigestWorkflow)` decorator wires it into the graph.
"""

from workflows import Workflow


class DigestWorkflow(Workflow):
    """Ingest → classify → parse → categorize → summarize → store → distribute.

    Steps are defined as unbound functions under `steps/` and attached here via
    `@step(workflow=DigestWorkflow)`, keeping this file free of business logic. The
    execution order is determined by each step's event type hints, not by the import
    order below.
    """


# Register the pipeline stages by importing them for their decorator side effects.
# Module imports (not `from ... import name`) are used so registration works no
# matter which module is imported first, avoiding partial-import errors.
import arxiv_digest.steps.categorization.step  # noqa: E402
import arxiv_digest.steps.classification.step  # noqa: E402
import arxiv_digest.steps.distribution.step  # noqa: E402
import arxiv_digest.steps.ingestion.step  # noqa: E402
import arxiv_digest.steps.parsing.step  # noqa: E402
import arxiv_digest.steps.storage.step  # noqa: E402
import arxiv_digest.steps.summarization.step  # noqa: E402, F401
