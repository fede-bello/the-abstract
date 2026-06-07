"""Weekly-issue endpoints. A "week" is derived from papers' ISO week — never stored."""

from fastapi import APIRouter

from arxiv_digest.api.models import WeekIssueOut, WeekSummaryOut
from arxiv_digest.clients import db

router = APIRouter(tags=["weeks"])


@router.get("/weeks")
async def list_weeks() -> list[WeekSummaryOut]:
    """Return one summary per ISO week that has papers, newest week first."""
    summaries = await db.list_week_summaries()
    return [WeekSummaryOut.model_validate(summary) for summary in summaries]


# Declared before "/weeks/{week_key}" so the literal path is matched first.
@router.get("/weeks/latest")
async def get_latest_week() -> WeekIssueOut | None:
    """Return the most recent ISO week's issue, or ``null`` if no papers are stored."""
    issue = await db.get_latest_week()
    return WeekIssueOut.model_validate(issue) if issue else None


@router.get("/weeks/{week_key}")
async def get_week(week_key: str) -> WeekIssueOut | None:
    """Return one ISO week's issue (e.g. ``2026-W23``), or ``null`` if it has no papers."""
    issue = await db.get_week(week_key)
    return WeekIssueOut.model_validate(issue) if issue else None
