"""Distribution logic: email the weekly HTML digest to each subscriber.

Reads the mailing list, generates one shared "insight of the week" paragraph, then renders
and sends a per-subscriber email — filtered to that subscriber's topic interests (no interests
means all topics). External I/O lives in the clients; this orchestrates them.
"""

import logging
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from arxiv_digest.clients.arxiv import Paper
from arxiv_digest.clients.db import get_active_subscribers
from arxiv_digest.clients.email import EmailError, send_email
from arxiv_digest.clients.llm import complete_structured
from arxiv_digest.config import settings
from arxiv_digest.steps.distribution.render import paper_matches_interests, render_digest_html

logger = logging.getLogger(__name__)

_INSIGHT_SYSTEM_PROMPT = (
    "You write the opener for a weekly machine-learning research digest. Each input line starts "
    "with the paper's [id]. Do two things. In `paragraph`, write ONE or TWO natural sentences "
    "naming the week's main theme or standout result, the single thing a busy researcher should "
    "take away. In `highlights`, list the ids of the 4 to 5 most notable papers, most important "
    "first, copying each bracketed [id] value exactly. No lists or markdown in the paragraph, no "
    "greeting, no sign-off. Do NOT use em dashes or en dashes anywhere; use commas, periods, or "
    "parentheses instead."
)


class WeeklyInsight(BaseModel):
    """The digest opener plus the ids of the week's standout (spotlight) papers."""

    paragraph: str
    highlights: list[str] = Field(default_factory=list)


def _format_week(papers: list[Paper]) -> str:
    """Render the week's papers as id-tagged lines for the insight + highlight prompt."""
    lines = []
    for paper in papers:
        topics = ", ".join(paper.topics) or "none"
        gist = paper.summary.short if paper.summary else paper.abstract
        lines.append(f"- [{paper.arxiv_id}] {paper.title} ({topics}): {gist}")
    return "\n".join(lines)


async def _summarize_week(papers: list[Paper]) -> tuple[str, list[str]]:
    """Return the weekly insight paragraph and the standout-paper ids; ``("", [])`` on failure."""
    try:
        insight = await complete_structured(
            _INSIGHT_SYSTEM_PROMPT,
            _format_week(papers),
            WeeklyInsight,
            model=settings.summarization_model,
            max_tokens=settings.weekly_insight_max_output_tokens,
            label="distribution",
        )
    except Exception:  # noqa: BLE001 — best-effort; the digest still sends without the insight
        logger.warning("weekly insight failed; sending digest without it", exc_info=True)
        return "", []
    return insight.paragraph, insight.highlights


def _papers_for(papers: list[Paper], interests: list[str]) -> list[Paper]:
    """Papers matching a subscriber's interests (all papers when interests is empty).

    Shares the interest-matching rule with the renderer's sectioning so the two never diverge.
    """
    return [paper for paper in papers if paper_matches_interests(paper, interests)]


def _digest_title() -> str:
    """The email subject line for this run's digest."""
    today = datetime.now(UTC).date()
    return f"arXiv ML Digest: week of {today:%Y-%m-%d}"


def _digest_heading() -> str:
    """The in-body heading (the template prints the 'arXiv ML Digest' wordmark above it)."""
    today = datetime.now(UTC).date()
    return f"Week of {today:%B} {today.day}, {today:%Y}"


def _unsubscribe_url(token: str) -> str | None:
    """The one-click unsubscribe link for a subscriber, or ``None`` if no base URL is configured."""
    base = settings.supabase_url.rstrip("/")
    return f"{base}/functions/v1/unsubscribe?token={token}" if base else None


async def send_digest(papers: list[Paper]) -> None:
    """Render and email the weekly digest to every active subscriber."""
    if not papers:
        logger.info("no papers to distribute; skipping digest")
        return
    subscribers = await get_active_subscribers()
    if not subscribers:
        logger.info("no active subscribers; skipping digest")
        return

    insight, highlights = await _summarize_week(papers)
    subject = _digest_title()
    heading = _digest_heading()
    for subscriber in subscribers:
        selected = _papers_for(papers, subscriber.interests)
        if not selected:
            continue
        unsubscribe_url = _unsubscribe_url(subscriber.unsubscribe_token)
        body = render_digest_html(
            heading,
            insight,
            selected,
            subscriber.interests,
            unsubscribe_url,
            highlights=highlights,
            site_url=settings.site_url or None,
        )
        try:
            await send_email(to=subscriber.email, subject=subject, html=body)
        except EmailError:
            logger.warning("failed to email %s; continuing", subscriber.email, exc_info=True)
