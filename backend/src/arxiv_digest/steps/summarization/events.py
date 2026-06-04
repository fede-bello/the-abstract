"""Events emitted by the summarization step."""

from workflows.events import Event

from arxiv_digest.clients.arxiv import Paper


class SummarizedEvent(Event):
    """Papers with short and long summaries, ready to be stored."""

    papers: list[Paper]
