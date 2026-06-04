"""Events emitted by the storage step."""

from workflows.events import Event

from arxiv_digest.clients.arxiv import Paper


class StoredEvent(Event):
    """Papers persisted to the database (with embeddings), ready for distribution."""

    papers: list[Paper]
