"""Parsing logic: parse a single useful paper's PDF into markdown."""

from arxiv_digest.clients.arxiv import Paper
from arxiv_digest.clients.parse import ParseError, parse_pdf_to_markdown


async def parse_paper(paper: Paper) -> Paper:
    """Parse a paper's PDF and return a copy with ``full_text`` populated.

    Raises ``ParseError`` (incl. when no PDF was downloaded) so the workflow can drop
    the paper and keep the rest of the run going.
    """
    if paper.pdf_path is None:
        msg = f"no pdf_path for {paper.arxiv_id}"
        raise ParseError(msg)
    markdown = await parse_pdf_to_markdown(paper.pdf_path)
    return paper.model_copy(update={"full_text": markdown})
