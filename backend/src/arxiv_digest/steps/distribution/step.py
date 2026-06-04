"""Distribution step (stub): render and send the weekly HTML digest email.

This is the final stage, so it emits ``StopEvent`` rather than a custom event.
"""

from workflows import step
from workflows.events import StopEvent

from arxiv_digest.steps.storage.events import StoredEvent
from arxiv_digest.workflows.ingest import DigestWorkflow


@step(workflow=DigestWorkflow)
async def distribute(ev: StoredEvent) -> StopEvent:
    """End the pipeline, returning the papers that flowed through.

    TODO: render the personalized HTML digest and send it to the subscriber list.
    """
    return StopEvent(result=ev.papers)
