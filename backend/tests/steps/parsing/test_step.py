"""Unit tests for the parsing step logic (LlamaParse client mocked)."""

from pathlib import Path

import pytest
from _builders import make_paper

from arxiv_digest.clients.parse import ParseError
from arxiv_digest.steps.parsing import step as parsing_step
from arxiv_digest.steps.parsing.step import parse_paper


async def test_parse_paper_populates_full_text(monkeypatch, tmp_path):
    async def fake_parse(pdf_path: Path) -> str:
        return f"# markdown for {pdf_path.name}"

    monkeypatch.setattr(parsing_step, "parse_pdf_to_markdown", fake_parse)
    paper = make_paper(pdf_path=tmp_path / "2401.00001.pdf")

    parsed = await parse_paper(paper)

    assert parsed.full_text == "# markdown for 2401.00001.pdf"
    assert paper.full_text is None  # original is not mutated


async def test_parse_paper_without_pdf_path_raises():
    paper = make_paper(pdf_path=None)

    with pytest.raises(ParseError, match="no pdf_path"):
        await parse_paper(paper)
