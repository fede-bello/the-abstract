"""Events emitted by the classification step."""

from workflows.events import Event

from arxiv_digest.clients.arxiv import Paper


class ClassifiedEvent(Event):
    """Papers that passed the useful-vs-noise classifier, ready for parsing."""

    papers: list[Paper]
