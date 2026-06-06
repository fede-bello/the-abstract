"""Unit tests for the storage step logic (embedding + DB clients mocked)."""

from _builders import make_paper

from arxiv_digest.steps.storage import step as storage_step
from arxiv_digest.steps.storage.step import store_papers


async def test_store_papers_chunks_embeds_and_persists(monkeypatch):
    embedded = {}
    persisted = {}

    async def fake_embed(texts):
        embedded["texts"] = texts
        return [[0.1, 0.2] for _ in texts]

    async def fake_db(papers, chunks):
        persisted["papers"] = papers
        persisted["chunks"] = chunks

    monkeypatch.setattr(storage_step, "embed_texts", fake_embed)
    monkeypatch.setattr(storage_step, "db_store_papers", fake_db)

    paper = make_paper(arxiv_id="2401.00001", full_text="Some parsed text. More of it.")
    result = await store_papers([paper])

    assert result == [paper]
    assert persisted["papers"] == [paper]
    chunks = persisted["chunks"]["2401.00001"]
    assert chunks
    assert [text for text, _ in chunks] == embedded["texts"]
    assert all(vector == [0.1, 0.2] for _, vector in chunks)


async def test_store_papers_without_full_text_persists_no_chunks(monkeypatch):
    captured = {}

    async def fake_embed(texts):
        return [[0.0] for _ in texts]

    async def fake_db(papers, chunks):
        captured["chunks"] = chunks

    monkeypatch.setattr(storage_step, "embed_texts", fake_embed)
    monkeypatch.setattr(storage_step, "db_store_papers", fake_db)

    await store_papers([make_paper(arxiv_id="2401.00002", full_text=None)])

    assert captured["chunks"] == {"2401.00002": []}
