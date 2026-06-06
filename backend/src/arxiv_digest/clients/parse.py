"""LlamaParse client: parse a paper's PDF into markdown via LlamaCloud (v2 SDK).

Uses the ``llama-cloud`` v2 client (``AsyncLlamaCloud``) and its ``parsing.parse``
convenience, which uploads the file, runs the job, polls to completion, and returns
the result. The parsing tier (cost vs accuracy) is configured by ``settings.parse_tier``.
"""

import asyncio
from pathlib import Path

from llama_cloud import AsyncLlamaCloud

from arxiv_digest.clients.usage import record_parse_usage
from arxiv_digest.config import settings

# Pin the parse API to the latest published spec; the SDK also accepts dated versions.
_PARSE_VERSION = "latest"


class ParseError(RuntimeError):
    """Raised when a PDF cannot be parsed (missing key, job failure, or empty result)."""


def _client() -> AsyncLlamaCloud:
    """Build the async LlamaCloud client from the configured API key."""
    api_key = settings.llama_cloud_api_key.get_secret_value()
    if not api_key:
        msg = "LLAMA_CLOUD_API_KEY is not set"
        raise ParseError(msg)
    return AsyncLlamaCloud(api_key=api_key)


async def parse_pdf_to_markdown(pdf_path: Path) -> str:
    """Parse a PDF into a single markdown string using the configured tier.

    Raises ``ParseError`` if the job returns no markdown so the caller can decide
    whether to drop the paper or fail the run.
    """
    pdf_bytes = await asyncio.to_thread(pdf_path.read_bytes)
    async with _client() as client:
        file = await client.files.create(
            file=(pdf_path.name, pdf_bytes),
            purpose="parse",
        )
        result = await client.parsing.parse(
            file_id=file.id,
            tier=settings.parse_tier,
            version=_PARSE_VERSION,
            expand=["markdown"],
            timeout=settings.parse_timeout_seconds,
        )

    # The v2 result returns markdown per page; join them into one document. A page
    # can be a "failed page" variant with no markdown, so read it defensively and skip.
    pages = result.markdown.pages if result.markdown else []
    # Record usage before the empty-markdown guard below: the job ran and is billable either way.
    await record_parse_usage(pages=len(pages), tier=settings.parse_tier)
    page_markdowns = [getattr(page, "markdown", None) for page in pages]
    full_text = "\n\n".join(md for md in page_markdowns if md)
    if not full_text:
        msg = f"LlamaParse returned no markdown for {pdf_path.name}"
        raise ParseError(msg)
    return full_text
