"""arXiv client: fetch recent ML-paper metadata and download their PDFs.

Grounded in the `arxiv` library (https://github.com/lukasschwab/arxiv.py) and the
arXiv API user manual. Each fetch run builds a fresh `arxiv.Client` configured with
a 5-second inter-request delay; transient throttling (429/503) is handled by our own
exponential backoff in `_search_with_backoff`.
"""

import asyncio
import logging
import random
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import arxiv
import httpx
from pydantic import BaseModel

from arxiv_digest.config import settings

logger = logging.getLogger(__name__)

# arXiv throttles with 429 (too many requests) and 503 (service busy). Both are
# transient, so we retry them with exponential backoff + jitter; other statuses
# (e.g. 400) fail fast. (Backoff timings are configurable in Settings.)
_RETRYABLE_STATUSES = frozenset({429, 503})


class Author(BaseModel):
    """A paper author. `affiliation` is populated only when arXiv provides it."""

    name: str
    affiliation: str | None = None


class Paper(BaseModel):
    """An arXiv paper: lightweight metadata plus the path to its downloaded PDF.

    The metadata (title, abstract, authors, affiliations, comment) feeds the
    classification step; `pdf_path` feeds the parsing step.
    """

    arxiv_id: str
    entry_id: str
    title: str
    abstract: str
    authors: list[Author]
    primary_category: str
    categories: list[str]
    comment: str | None = None
    journal_ref: str | None = None
    doi: str | None = None
    published: datetime
    updated: datetime
    pdf_url: str
    pdf_path: Path | None = None
    # Full parsed text (markdown), populated by the parsing step for useful papers.
    full_text: str | None = None


def _build_query(categories: list[str], days_back: int) -> str:
    """Build an arXiv query: any of the categories, submitted within the last `days_back` days.

    The arXiv API expects the submission window as a GMT ``[start TO end]`` range
    formatted as ``YYYYMMDDHHMM``.
    """
    category_clause = " OR ".join(f"cat:{category}" for category in categories)
    now = datetime.now(UTC)
    start = now - timedelta(days=days_back)
    window = f"submittedDate:[{start:%Y%m%d%H%M} TO {now:%Y%m%d%H%M}]"
    return f"({category_clause}) AND {window}"


def _download_pdf(url: str, dest: Path) -> None:
    """Stream a PDF to `dest`. Runs in a worker thread, so a sync httpx call is fine.

    The `arxiv` library dropped `Result.download_pdf` in 4.x, so we fetch the
    published `pdf_url` ourselves; this also keeps the download in the client layer.
    """
    timeout = settings.arxiv_pdf_download_timeout_seconds
    with httpx.stream("GET", url, follow_redirects=True, timeout=timeout) as response:
        response.raise_for_status()
        with dest.open("wb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)


def _author_affiliation(author: arxiv.Result.Author) -> str | None:
    """Normalize an author's affiliation across `arxiv` versions (2.x str, 4.x list)."""
    affiliation = getattr(author, "affiliation", None)
    if isinstance(affiliation, list):
        return "; ".join(affiliation) if affiliation else None
    return affiliation or None


def _to_paper(result: arxiv.Result, pdf_dir: Path) -> Paper:
    """Download a result's PDF and map the arXiv result onto our `Paper` model."""
    arxiv_id = result.get_short_id()
    filename = f"{arxiv_id.replace('/', '_')}.pdf"
    pdf_path = pdf_dir / filename
    _download_pdf(result.pdf_url, pdf_path)
    return Paper(
        arxiv_id=arxiv_id,
        entry_id=result.entry_id,
        title=result.title.strip(),
        abstract=result.summary.strip(),
        authors=[Author(name=a.name, affiliation=_author_affiliation(a)) for a in result.authors],
        primary_category=result.primary_category,
        categories=list(result.categories),
        comment=result.comment,
        journal_ref=result.journal_ref,
        doi=result.doi,
        published=result.published,
        updated=result.updated,
        pdf_url=result.pdf_url,
        pdf_path=pdf_path,
    )


def _search_with_backoff(
    client: arxiv.Client,
    search: arxiv.Search,
    max_attempts: int,
) -> list[arxiv.Result]:
    """Run the arXiv search, retrying on 429/503 with exponential backoff + jitter.

    `max_attempts` is the total number of tries. Non-retryable HTTP errors propagate
    immediately, as does the final attempt's error once retries are exhausted.
    """
    delay = settings.arxiv_retry_base_delay_seconds
    for attempt in range(1, max_attempts):
        try:
            return list(client.results(search))
        except arxiv.HTTPError as exc:
            if exc.status not in _RETRYABLE_STATUSES:
                raise
            capped = min(delay, settings.arxiv_retry_max_delay_seconds)
            sleep_for = capped + random.uniform(0.0, 1.0)  # noqa: S311
            logger.warning(
                "arXiv returned HTTP %s; backing off %.0fs (attempt %d/%d)",
                exc.status,
                sleep_for,
                attempt,
                max_attempts,
            )
            time.sleep(sleep_for)
            delay *= 2
    # Final attempt: return its results, or let the exception propagate.
    return list(client.results(search))


def _fetch_sync(
    categories: list[str],
    max_results: int,
    days_back: int,
    pdf_dir: Path,
    max_attempts: int,
) -> list[Paper]:
    """Synchronously query arXiv and download PDFs (runs in a worker thread)."""
    pdf_dir.mkdir(parents=True, exist_ok=True)
    # With arxiv_num_retries=1, each attempt is one request and our own backoff
    # (below) handles spacing — keeping a long-running retry loop polite.
    client = arxiv.Client(
        page_size=settings.arxiv_page_size,
        delay_seconds=settings.arxiv_request_delay_seconds,
        num_retries=settings.arxiv_num_retries,
    )
    search = arxiv.Search(
        query=_build_query(categories, days_back),
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )
    results = _search_with_backoff(client, search, max_attempts)
    return [_to_paper(result, pdf_dir) for result in results]


async def fetch_recent_papers(
    categories: list[str],
    max_results: int,
    days_back: int,
    pdf_dir: Path,
    max_attempts: int,
) -> list[Paper]:
    """Fetch papers in `categories` submitted in the last `days_back` days, downloading each PDF.

    Retries the search on transient arXiv throttling (429/503) up to `max_attempts`
    times with exponential backoff. The `arxiv` library is synchronous and
    network-bound, so the work runs in a thread to avoid blocking the event loop.
    """
    return await asyncio.to_thread(
        _fetch_sync,
        categories,
        max_results,
        days_back,
        pdf_dir,
        max_attempts,
    )
