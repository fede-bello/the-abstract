"""Events emitted around the parsing step."""

from workflows.events import Event

from arxiv_digest.clients.arxiv import Paper


class ParsePaperEvent(Event):
    """A useful paper to parse (fan-out unit, emitted only for useful papers)."""

    paper: Paper


class PaperResolvedEvent(Event):
    """Terminal per-paper outcome: the parsed paper, or ``None`` if dropped.

    A paper is dropped when it was classified as noise, or when parsing failed.
    Every fanned-out paper produces exactly one of these, so the fan-in can count
    them against the total.
    """

    paper: Paper | None


class ParsedEvent(Event):
    """Papers with full parsed content, ready for categorization."""

    papers: list[Paper]
