"""Distribution logic: email the weekly HTML digest to each subscriber.

Reads the mailing list, generates one shared "insight of the week" paragraph, then renders
and sends a per-subscriber email — filtered to that subscriber's topic interests (no interests
means all topics). External I/O lives in the clients; this orchestrates them.
"""

import logging
from datetime import UTC, datetime

from pydantic import BaseModel

from arxiv_digest.clients.arxiv import Paper
from arxiv_digest.clients.db import get_active_subscribers
from arxiv_digest.clients.email import EmailError, send_email
from arxiv_digest.clients.llm import complete_structured
from arxiv_digest.config import settings
from arxiv_digest.steps.distribution.render import paper_matches_interests, render_digest_html

logger = logging.getLogger(__name__)

_INSIGHT_SYSTEM_PROMPT = (
    "You write the one-line opener for a weekly machine-learning research digest. Given this "
    "week's papers, write ONE or TWO punchy sentences naming the week's main theme or standout "
    "result — the single thing a busy researcher should take away. No lists, no greeting, no "
    "sign-off; just the sentence(s)."
)


class WeeklyInsight(BaseModel):
    """The one-paragraph overview that opens the digest."""

    paragraph: str


def _format_week(papers: list[Paper]) -> str:
    """Render the week's papers as bullet lines for the insight prompt."""
    lines = []
    for paper in papers:
        topics = ", ".join(paper.topics) or "—"
        gist = paper.summary.short if paper.summary else paper.abstract
        lines.append(f"- {paper.title} [{topics}]: {gist}")
    return "\n".join(lines)


async def _summarize_week(papers: list[Paper]) -> str:
    """Generate the shared weekly insight paragraph; empty string if the LLM call fails."""
    try:
        insight = await complete_structured(
            _INSIGHT_SYSTEM_PROMPT,
            _format_week(papers),
            WeeklyInsight,
            model=settings.summarization_model,
            max_tokens=settings.weekly_insight_max_output_tokens,
        )
    except Exception:  # noqa: BLE001 — best-effort; the digest still sends without the insight
        logger.warning("weekly insight failed; sending digest without it", exc_info=True)
        return ""
    return insight.paragraph


def _papers_for(papers: list[Paper], interests: list[str]) -> list[Paper]:
    """Papers matching a subscriber's interests (all papers when interests is empty).

    Shares the interest-matching rule with the renderer's sectioning so the two never diverge.
    """
    return [paper for paper in papers if paper_matches_interests(paper, interests)]


def _digest_title() -> str:
    """Subject line and body heading for this run's digest."""
    today = datetime.now(UTC).date()
    return f"arXiv ML Digest — week of {today:%Y-%m-%d}"


async def send_digest(papers: list[Paper]) -> None:
    """Render and email the weekly digest to every active subscriber."""
    if not papers:
        logger.info("no papers to distribute; skipping digest")
        return
    subscribers = await get_active_subscribers()
    if not subscribers:
        logger.info("no active subscribers; skipping digest")
        return

    insight = await _summarize_week(papers)
    title = _digest_title()
    for subscriber in subscribers:
        selected = _papers_for(papers, subscriber.interests)
        if not selected:
            continue
        body = render_digest_html(title, insight, selected, subscriber.interests)
        try:
            await send_email(to=subscriber.email, subject=title, html=body)
        except EmailError:
            logger.warning("failed to email %s; continuing", subscriber.email, exc_info=True)
