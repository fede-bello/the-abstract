"""Unit tests for the storage step logic (DB client mocked)."""

from _builders import make_paper

from arxiv_digest.steps.storage import step as storage_step
from arxiv_digest.steps.storage.step import store_papers


async def test_store_papers_persists_and_returns_papers(monkeypatch):
    persisted = {}

    async def fake_db(papers):
        persisted["papers"] = papers

    monkeypatch.setattr(storage_step, "db_store_papers", fake_db)

    papers = [make_paper(arxiv_id="2401.00001"), make_paper(arxiv_id="2401.00002")]
    result = await store_papers(papers)

    assert result == papers
    assert persisted["papers"] == papers
