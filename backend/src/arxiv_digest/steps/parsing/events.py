"""Events emitted by the parsing step."""

from workflows.events import Event

from arxiv_digest.clients.arxiv import Paper


class ParsedEvent(Event):
    """Papers with full parsed content (text, figures, tables), ready for categorization."""

    papers: list[Paper]
