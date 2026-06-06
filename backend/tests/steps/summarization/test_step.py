"""Unit tests for the summarization step logic (LLM client mocked)."""

from _builders import make_paper

from arxiv_digest.clients.arxiv import Summary
from arxiv_digest.steps.summarization import step as summ_step
from arxiv_digest.steps.summarization.step import summarize_paper

_SUMMARY = Summary(short="- a\n- b", long="para one.\n\npara two.", conclusions="matters.")


async def test_summarize_paper_returns_the_models_summary(monkeypatch):
    async def fake_complete(system, user, schema, *, model, max_tokens):
        return _SUMMARY

    monkeypatch.setattr(summ_step, "complete_structured", fake_complete)

    assert await summarize_paper(make_paper()) == _SUMMARY


async def test_summarize_paper_feeds_the_parsed_body_to_the_model(monkeypatch):
    seen = {}

    async def fake_complete(system, user, schema, *, model, max_tokens):
        seen["user"] = user
        return _SUMMARY

    monkeypatch.setattr(summ_step, "complete_structured", fake_complete)

    await summarize_paper(make_paper(full_text="THE PARSED BODY"))

    assert "THE PARSED BODY" in seen["user"]
