"""Offline end-to-end tests for the classify -> ((parse -> summarize) ∥ categorize) flow.

The LLM and LlamaParse boundaries are stubbed, so these run with no network and exercise
the workflow's routing: useful papers get parsed, summarized + tagged and survive, noise
papers are dropped, parse failures are dropped, and an empty run completes cleanly.
"""

from _builders import make_paper

from arxiv_digest.clients.arxiv import Paper, Summary
from arxiv_digest.clients.parse import ParseError
from arxiv_digest.steps.classification.step import ClassificationResult
from arxiv_digest.workflows import digest


def _useful(paper: Paper) -> bool:
    return paper.arxiv_id.startswith("u")


async def _fake_classify(paper: Paper) -> ClassificationResult:
    label = "useful" if _useful(paper) else "noise"
    return ClassificationResult(label=label, rationale="r")


async def _fake_parse(paper: Paper) -> Paper:
    if paper.arxiv_id == "u-fail":
        msg = "boom"
        raise ParseError(msg)
    return paper.model_copy(update={"full_text": f"md-{paper.arxiv_id}"})


async def _fake_categorize(paper: Paper) -> list[str]:
    return [f"topic-{paper.arxiv_id}"]


async def _fake_summarize(paper: Paper) -> Summary:
    return Summary(short=f"short-{paper.arxiv_id}", long="long", conclusions="impact")


async def _fake_store(papers: list[Paper]) -> list[Paper]:
    return papers


async def _fake_send_digest(papers: list[Paper]) -> None:
    return None


def _patch(monkeypatch, papers: list[Paper]) -> None:
    async def fake_fetch(max_results: int, days_back: int) -> list[Paper]:
        return papers

    monkeypatch.setattr(digest, "fetch_papers", fake_fetch)
    monkeypatch.setattr(digest, "classify_paper", _fake_classify)
    monkeypatch.setattr(digest, "parse_paper", _fake_parse)
    monkeypatch.setattr(digest, "categorize_paper", _fake_categorize)
    monkeypatch.setattr(digest, "summarize_paper", _fake_summarize)
    monkeypatch.setattr(digest, "store_papers", _fake_store)
    monkeypatch.setattr(digest, "send_digest", _fake_send_digest)


async def test_keeps_useful_parsed_drops_noise_and_failures(monkeypatch):
    papers = [
        make_paper(arxiv_id="u-1"),
        make_paper(arxiv_id="n-1"),
        make_paper(arxiv_id="u-2"),
        make_paper(arxiv_id="u-fail"),
        make_paper(arxiv_id="n-2"),
    ]
    _patch(monkeypatch, papers)

    result: list[Paper] = await digest.DigestWorkflow(timeout=30).run()

    assert {p.arxiv_id for p in result} == {"u-1", "u-2"}
    assert all(p.full_text == f"md-{p.arxiv_id}" for p in result)
    assert all(p.topics == [f"topic-{p.arxiv_id}"] for p in result)
    assert all(p.summary is not None and p.summary.short == f"short-{p.arxiv_id}" for p in result)
    assert all(p.classification_rationale == "r" for p in result)


async def test_empty_run_completes_with_no_papers(monkeypatch):
    _patch(monkeypatch, [])

    result: list[Paper] = await digest.DigestWorkflow(timeout=30).run()

    assert result == []
