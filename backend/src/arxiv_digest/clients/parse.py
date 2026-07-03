"""LiteParse client: parse a paper's PDF into markdown locally (no cloud, no API key).

Uses ``liteparse`` (run-llama/liteparse), a native Rust/PyO3 parser that renders a PDF's
spatial layout to markdown. arXiv PDFs are born-digital, so PDFium embedded-text extraction
is enough and OCR stays off by default (``settings.parse_ocr_enabled``) — that keeps a parse
to a fraction of a second instead of the ~100x slower OCR fallback. Parsing is synchronous and
CPU-bound, so it runs in a worker thread to keep the event loop free.
"""

import asyncio
from pathlib import Path

from liteparse import LiteParse

from arxiv_digest.clients.usage import record_parse_usage
from arxiv_digest.config import settings


class ParseError(RuntimeError):
    """Raised when a PDF cannot be parsed (parser failure or empty result)."""


# One reusable parser: markdown out, images dropped (the summarizer wants prose, not figures),
# links dropped (noise for summarization). OCR is a config toggle, off for born-digital arXiv PDFs.
_PARSER = LiteParse(
    output_format="markdown",
    image_mode="off",
    extract_links=False,
    ocr_enabled=settings.parse_ocr_enabled,
    quiet=True,
)


async def parse_pdf_to_markdown(pdf_path: Path) -> str:
    """Parse a PDF into a single markdown string.

    Raises ``ParseError`` if the parser returns no text so the caller can decide whether to
    drop the paper or fail the run.
    """
    result = await asyncio.to_thread(_PARSER.parse, str(pdf_path))
    # Record volume before the empty guard: the parse ran either way. LiteParse is local ($0),
    # so this is pages-only accounting, not billing.
    await record_parse_usage(pages=result.num_pages)
    full_text = result.text.strip()
    if not full_text:
        msg = f"LiteParse returned no text for {pdf_path.name}"
        raise ParseError(msg)
    return full_text
