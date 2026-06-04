"""Events emitted by the categorization step."""

from workflows.events import Event

from arxiv_digest.clients.arxiv import Paper


class CategorizedEvent(Event):
    """Papers tagged with one or more topic categories, ready for summarization."""

    papers: list[Paper]
