"""Events emitted around the summarization step."""

from workflows.events import Event

from arxiv_digest.clients.arxiv import Paper


class SummarizePaperEvent(Event):
    """A parsed useful paper to summarize (chained after parsing, before the join)."""

    paper: Paper
