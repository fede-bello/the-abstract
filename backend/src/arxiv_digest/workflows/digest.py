"""The `DigestWorkflow` definition.

Kept separate from the step wiring (`ingest.py`) so the steps can import the
workflow class without creating a circular import.
"""

from workflows import Workflow


class DigestWorkflow(Workflow):
    """Ingest -> classify -> parse -> categorize -> summarize -> store -> distribute.

    Event-driven: steps are unbound functions under `steps/`, each attached via
    ``@step(workflow=DigestWorkflow)``. The explicit pipeline order lives in
    `arxiv_digest.workflows.ingest`.
    """
