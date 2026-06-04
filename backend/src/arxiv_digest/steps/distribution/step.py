"""Distribution logic: render and send the weekly HTML digest email."""

import logging

from arxiv_digest.clients.arxiv import Paper

logger = logging.getLogger(__name__)


async def send_digest(papers: list[Paper]) -> None:
    """Render the personalized HTML digest and email it to subscribers.

    TODO: build the HTML and send via the email client. No-op for now.
    """
    logger.info("Digest stub: would send %d papers", len(papers))
