"""Unit tests for the categorization step logic (LLM client mocked)."""

from _builders import make_paper

from arxiv_digest.steps.categorization import step as cat_step
from arxiv_digest.steps.categorization.step import PaperTopics, categorize_paper


async def test_categorize_paper_returns_selected_titles(monkeypatch):
    async def fake_complete(system, user, schema):
        return PaperTopics(llms=True, efficient_ml=True)

    monkeypatch.setattr(cat_step, "complete_structured", fake_complete)

    topics = await categorize_paper(make_paper())

    assert topics == ["LLMs", "Efficient ML"]


async def test_categorize_paper_no_match_returns_empty(monkeypatch):
    async def fake_complete(system, user, schema):
        return PaperTopics()

    monkeypatch.setattr(cat_step, "complete_structured", fake_complete)

    assert await categorize_paper(make_paper()) == []


def test_every_topic_field_has_a_title():
    assert all(field.title for field in PaperTopics.model_fields.values())
