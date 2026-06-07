"""Taxonomy endpoints: topic facet counts and the arXiv categories present."""

from fastapi import APIRouter

from arxiv_digest.api.models import TopicCountOut
from arxiv_digest.clients import db
from arxiv_digest.steps.categorization.step import taxonomy_titles

router = APIRouter(tags=["meta"])


@router.get("/topics")
async def list_topics() -> list[TopicCountOut]:
    """Return topic facets in taxonomy order, omitting topics no stored paper carries."""
    counts = await db.list_topic_counts()
    return [
        TopicCountOut(title=title, count=count)
        for title in taxonomy_titles()
        if (count := counts.get(title, 0)) > 0
    ]


@router.get("/categories")
async def list_categories() -> list[str]:
    """Return the distinct arXiv category codes present across all stored papers."""
    return await db.list_categories()
