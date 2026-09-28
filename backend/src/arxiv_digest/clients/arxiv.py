"""arXiv client: fetch recent ML-paper metadata and download their PDFs.

Metadata comes from arXiv's OAI-PMH interface (https://info.arxiv.org/help/oa/index.html)
in the ``arXivRaw`` format, one per-category set at a time (``cs.LG`` -> ``cs:cs:LG``).
We don't use the search API (``export.arxiv.org/api/query``): since Sep 2026 it answers
most requests with an empty HTTP 406, while OAI-PMH, arXiv's recommended interface for
bulk harvesting, keeps working from CI runners. OAI filters by datestamp (last metadata
change), so we harvest from the window start and keep only papers whose first version
was submitted inside it.
"""

import asyncio
import logging
import random
import re
import time
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx
from pydantic import BaseModel, Field

from arxiv_digest.config import settings

logger = logging.getLogger(__name__)

_OAI_URL = "https://oaipmh.arxiv.org/oai"
_NS = {"oai": "http://www.openarchives.org/OAI/2.0/", "raw": "http://arxiv.org/OAI/arXivRaw/"}
_ABS_URL = "http://arxiv.org/abs/{arxiv_id}"
_PDF_URL = "https://arxiv.org/pdf/{arxiv_id}"

# arXiv throttles with 429 (too many requests) and 503 (service busy, usually with a
# Retry-After header for OAI flow control). Both are transient, so we retry them,
# honoring Retry-After when present and otherwise backing off exponentially with jitter;
# other statuses fail fast. (Backoff timings are configurable in Settings.)
_RETRYABLE_STATUSES = frozenset({429, 503})

# arXivRaw lists authors as one string: "A, B (Univ X, Lab Y) and C". Split on commas
# and " and " only outside parentheses, since affiliations can contain both.
_AUTHOR_SEPARATOR = re.compile(r",\s*(?:and\s+)?|\s+and\s+")
_AFFILIATION = re.compile(r"^(?P<name>[^()]+?)\s*\((?P<affiliation>.+)\)$")


class ArxivError(RuntimeError):
    """Raised when arXiv's OAI-PMH endpoint fails or returns an OAI error."""


class Author(BaseModel):
    """A paper author. `affiliation` is populated only when arXiv provides it."""

    name: str
    affiliation: str | None = None


class Summary(BaseModel):
    """Generated summaries for one paper — the LLM output schema and the stored value."""

    short: str
    long: str
    conclusions: str


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
    full_text: str | None = None
    topics: list[str] = Field(default_factory=list)
    summary: Summary | None = None
    classification_rationale: str | None = None


class OaiPage(BaseModel):
    """One ``ListRecords`` response: its papers and the token for the next page, if any."""

    papers: list[Paper]
    resumption_token: str | None = None


def _text(metadata: ET.Element, tag: str) -> str | None:
    """Whitespace-normalized text of the ``raw:<tag>`` child, or None if absent or empty."""
    child = metadata.find(f"raw:{tag}", _NS)
    if child is None or child.text is None:
        return None
    return " ".join(child.text.split()) or None


def _parse_authors(authors: str) -> list[Author]:
    """Parse an arXivRaw author string, splitting only at separators outside parentheses."""
    names: list[str] = []
    last = 0
    for separator in _AUTHOR_SEPARATOR.finditer(authors):
        before = authors[: separator.start()]
        if before.count("(") == before.count(")"):
            names.append(authors[last : separator.start()])
            last = separator.end()
    names.append(authors[last:])
    parsed: list[Author] = []
    for raw_name in filter(None, (name.strip() for name in names)):
        if match := _AFFILIATION.match(raw_name):
            parsed.append(Author(name=match["name"], affiliation=match["affiliation"]))
        else:
            parsed.append(Author(name=raw_name))
    return parsed


def _to_paper(metadata: ET.Element) -> Paper:
    """Map one ``arXivRaw`` metadata element onto a `Paper` (PDF not downloaded yet)."""
    versions = metadata.findall("raw:version", _NS)
    dates = [parsedate_to_datetime(v.findtext("raw:date", "", _NS)) for v in versions]
    arxiv_id = f"{_text(metadata, 'id')}{versions[-1].get('version')}"
    categories = (_text(metadata, "categories") or "").split()
    return Paper(
        arxiv_id=arxiv_id,
        entry_id=_ABS_URL.format(arxiv_id=arxiv_id),
        title=_text(metadata, "title") or "",
        abstract=(metadata.findtext("raw:abstract", "", _NS)).strip(),
        authors=_parse_authors(_text(metadata, "authors") or ""),
        primary_category=categories[0],
        categories=categories,
        comment=_text(metadata, "comments"),
        journal_ref=_text(metadata, "journal-ref"),
        doi=_text(metadata, "doi"),
        published=dates[0],
        updated=dates[-1],
        pdf_url=_PDF_URL.format(arxiv_id=arxiv_id),
    )


def parse_list_records(content: bytes) -> OaiPage:
    """Parse an OAI-PMH ``ListRecords`` response in the ``arXivRaw`` format.

    Deleted records (no metadata) are skipped; ``noRecordsMatch`` is an empty page, and
    any other OAI error raises `ArxivError`.
    """
    root = ET.fromstring(content)  # noqa: S314 (trusted source; expat skips external entities)
    if (error := root.find("oai:error", _NS)) is not None:
        if error.get("code") == "noRecordsMatch":
            return OaiPage(papers=[])
        msg = f"arXiv OAI-PMH error {error.get('code')}: {error.text}"
        raise ArxivError(msg)
    records = root.find("oai:ListRecords", _NS)
    if records is None:
        msg = "arXiv OAI-PMH response has neither ListRecords nor an error"
        raise ArxivError(msg)
    papers = [
        _to_paper(metadata)
        for metadata in records.iterfind("oai:record/oai:metadata/raw:arXivRaw", _NS)
    ]
    token = records.findtext("oai:resumptionToken", "", _NS).strip()
    return OaiPage(papers=papers, resumption_token=token or None)


def select_recent(papers: list[Paper], since: datetime, max_results: int) -> list[Paper]:
    """Newest-first papers first submitted at or after `since`, deduplicated, capped."""
    unique = {paper.arxiv_id: paper for paper in papers if paper.published >= since}
    return sorted(unique.values(), key=lambda paper: paper.published, reverse=True)[:max_results]


def _set_spec(category: str) -> str:
    """OAI set for an arXiv category: ``cs.LG`` -> ``cs:cs:LG``, a bare archive -> itself."""
    archive, _, subject = category.partition(".")
    return f"{archive}:{archive}:{subject}" if subject else archive


def _retry_after(response: httpx.Response) -> float | None:
    """Seconds from a numeric Retry-After header, if the server sent one."""
    value = response.headers.get("retry-after", "")
    return float(value) if value.isdigit() else None


def _get_page(client: httpx.Client, params: dict[str, str], max_attempts: int) -> OaiPage:
    """GET one OAI page, retrying 429/503 up to `max_attempts` tries in total."""
    delay = settings.arxiv_retry_base_delay_seconds
    for attempt in range(1, max_attempts + 1):
        response = client.get(_OAI_URL, params=params)
        if response.status_code not in _RETRYABLE_STATUSES or attempt == max_attempts:
            break
        backoff = min(delay, settings.arxiv_retry_max_delay_seconds) + random.uniform(0.0, 1.0)  # noqa: S311
        sleep_for = _retry_after(response) or backoff
        logger.warning(
            "arXiv returned HTTP %s; backing off %.0fs (attempt %d/%d)",
            response.status_code,
            sleep_for,
            attempt,
            max_attempts,
        )
        time.sleep(sleep_for)
        delay *= 2
    if response.is_error:
        msg = f"arXiv OAI-PMH returned HTTP {response.status_code} for {response.url}"
        raise ArxivError(msg)
    return parse_list_records(response.content)


def _harvest(
    client: httpx.Client, category: str, since: datetime, max_attempts: int
) -> Iterator[Paper]:
    """Yield every paper in `category`'s set whose metadata changed since `since`."""
    params = {
        "verb": "ListRecords",
        "metadataPrefix": "arXivRaw",
        "set": _set_spec(category),
        "from": since.date().isoformat(),
    }
    while True:
        page = _get_page(client, params, max_attempts)
        yield from page.papers
        if page.resumption_token is None:
            return
        time.sleep(settings.arxiv_request_delay_seconds)
        params = {"verb": "ListRecords", "resumptionToken": page.resumption_token}


def _download_pdf(url: str, dest: Path) -> None:
    """Stream a PDF to `dest`. Runs in a worker thread, so a sync httpx call is fine."""
    timeout = settings.arxiv_pdf_download_timeout_seconds
    with httpx.stream("GET", url, follow_redirects=True, timeout=timeout) as response:
        response.raise_for_status()
        with dest.open("wb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)


def _with_pdf(paper: Paper, pdf_dir: Path) -> Paper:
    """Download a paper's PDF into `pdf_dir` and return the paper pointing at it."""
    pdf_path = pdf_dir / f"{paper.arxiv_id.replace('/', '_')}.pdf"
    _download_pdf(paper.pdf_url, pdf_path)
    return paper.model_copy(update={"pdf_path": pdf_path})


def _fetch_sync(
    categories: list[str],
    max_results: int,
    days_back: int,
    pdf_dir: Path,
    max_attempts: int,
) -> list[Paper]:
    """Synchronously harvest arXiv and download PDFs (runs in a worker thread)."""
    pdf_dir.mkdir(parents=True, exist_ok=True)
    since = datetime.now(UTC) - timedelta(days=days_back)
    harvested: list[Paper] = []
    with httpx.Client(timeout=settings.arxiv_request_timeout_seconds) as client:
        for index, category in enumerate(categories):
            if index:
                time.sleep(settings.arxiv_request_delay_seconds)
            harvested.extend(_harvest(client, category, since, max_attempts))
    recent = select_recent(harvested, since, max_results)
    logger.info(
        "Harvested %d arXiv records; %d recent papers selected", len(harvested), len(recent)
    )
    return [_with_pdf(paper, pdf_dir) for paper in recent]


async def fetch_recent_papers(
    categories: list[str],
    max_results: int,
    days_back: int,
    pdf_dir: Path,
    max_attempts: int,
) -> list[Paper]:
    """Fetch papers in `categories` submitted in the last `days_back` days, downloading each PDF.

    Returns at most `max_results` papers, newest first. Each OAI request retries arXiv
    throttling (429/503) up to `max_attempts` times. The harvest and downloads are
    synchronous and network-bound, so they run in a thread to keep the event loop free.
    """
    return await asyncio.to_thread(
        _fetch_sync,
        categories,
        max_results,
        days_back,
        pdf_dir,
        max_attempts,
    )
