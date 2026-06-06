"""Events emitted around the parsing step."""

from workflows.events import Event

from arxiv_digest.clients.arxiv import Paper


class ParsePaperEvent(Event):
    """A useful paper to parse (fan-out unit, runs in parallel with categorization)."""

    paper: Paper


class ParsedPaperEvent(Event):
    """The parse outcome for one paper, keyed by id for the per-paper join.

    ``paper`` is ``None`` when parsing failed (the paper is then dropped).
    """

    arxiv_id: str
    paper: Paper | None
