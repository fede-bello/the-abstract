"""Events emitted around the categorization step."""

from workflows.events import Event

from arxiv_digest.clients.arxiv import Paper


class CategorizePaperEvent(Event):
    """A useful paper to categorize (fan-out unit, runs in parallel with parsing)."""

    paper: Paper


class TopicsAssignedEvent(Event):
    """The topics assigned to one paper, keyed by id for the per-paper join."""

    arxiv_id: str
    topics: list[str]


class PaperResolvedEvent(Event):
    """Terminal per-paper outcome after parse + categorize join, or ``None`` if dropped."""

    paper: Paper | None


class CategorizedEvent(Event):
    """Papers with parsed content, summaries, and topic tags — the post-join aggregate."""

    papers: list[Paper]
