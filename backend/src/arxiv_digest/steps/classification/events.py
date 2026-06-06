"""Events emitted by the classification step."""

from workflows.events import Event

from arxiv_digest.clients.arxiv import Paper


class ClassifyPaperEvent(Event):
    """A single paper to classify (one fan-out unit)."""

    paper: Paper
