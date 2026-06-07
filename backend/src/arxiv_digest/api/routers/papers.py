"""Paper endpoints: list with filters, and fetch one by arXiv id."""

from typing import Annotated

from fastapi import APIRouter, Query

from arxiv_digest.api.models import PaperOut
from arxiv_digest.clients import db

router = APIRouter(tags=["papers"])


@router.get("/papers")
async def list_papers(
    topic: Annotated[list[str] | None, Query()] = None,
    category: Annotated[list[str] | None, Query()] = None,
    from_: Annotated[str | None, Query(alias="from")] = None,
    to: Annotated[str | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
) -> list[PaperOut]:
    """Return papers matching the filters, newest first. All filters are optional and AND together.

    ``topic`` and ``category`` are repeatable; ``from``/``to`` are inclusive ``YYYY-MM-DD``
    bounds; ``q`` is a keyword over title, abstract and authors.
    """
    papers = await db.list_papers(
        topics=topic, categories=category, date_from=from_, date_to=to, q=q
    )
    return [PaperOut.model_validate(paper) for paper in papers]


@router.get("/papers/{arxiv_id}")
async def get_paper(arxiv_id: str) -> PaperOut | None:
    """Return one paper by arXiv id, or ``null`` if it is not stored."""
    paper = await db.get_paper(arxiv_id)
    return PaperOut.model_validate(paper) if paper else None
