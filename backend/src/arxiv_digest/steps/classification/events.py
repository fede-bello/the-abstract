"""Events emitted by the classification step."""

from workflows.events import Event

from arxiv_digest.clients.arxiv import Paper
from arxiv_digest.steps.classification.step import ClassificationResult


class ClassifyPaperEvent(Event):
    """A single paper to classify (one fan-out unit)."""

    paper: Paper


class PaperClassifiedEvent(Event):
    """A paper plus its verdict (one fan-in unit)."""

    paper: Paper
    result: ClassificationResult


class ClassifiedEvent(Event):
    """Papers that passed the useful-vs-noise classifier, ready for parsing."""

    papers: list[Paper]
