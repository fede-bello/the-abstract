"""Events emitted by the ingestion step."""

from workflows.events import Event

from arxiv_digest.clients.arxiv import Paper


class PapersFetchedEvent(Event):
    """Papers pulled from arXiv (metadata + downloaded PDFs), ready for classification."""

    papers: list[Paper]
