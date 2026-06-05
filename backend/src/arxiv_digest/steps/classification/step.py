"""Classification logic: judge a single paper as useful vs noise (LLM over metadata).

Per-paper logic only. Concurrency and the useful/noise filtering are orchestration
concerns handled by ``DigestWorkflow`` via per-paper fan-out (``@step(num_workers=N)``).
"""

from typing import Literal

from pydantic import BaseModel

from arxiv_digest.clients.arxiv import Author, Paper
from arxiv_digest.clients.llm import complete_structured

_SYSTEM_PROMPT = (
    "You curate a weekly machine-learning research digest. For each arXiv paper, decide "
    "whether it is USEFUL (worth featuring) or NOISE (skip), judging ONLY the metadata "
    "provided (title, authors, category, comment, abstract).\n\n"
    "Mark USEFUL when the abstract shows any of: a novel architectural or theoretical "
    "contribution; a strong or surprising empirical result; clear real-world applicability "
    "or downstream impact; or a provocative, well-scoped idea worth researchers' attention.\n"
    "Mark NOISE when it is an incremental tweak, a narrow domain-specific application with no "
    "broader ML relevance, or a survey/review with no new method.\n\n"
    "Judge the CONTRIBUTION, not the fame of the authors or institutions — many strong papers "
    "come from little-known groups, and weak papers come from famous ones. The bar is "
    "permissive: when genuinely borderline, lean USEFUL. Give a one-sentence rationale."
)


class ClassificationResult(BaseModel):
    """The classifier's verdict for one paper."""

    label: Literal["useful", "noise"]
    rationale: str


def _format_authors(authors: list[Author]) -> str:
    """Render authors as a comma-separated list, including affiliations when present."""
    parts = [a.name if a.affiliation is None else f"{a.name} ({a.affiliation})" for a in authors]
    return ", ".join(parts) if parts else "—"


def _format_metadata(paper: Paper) -> str:
    """Render a paper's lightweight metadata as the classifier's user prompt."""
    return (
        f"Title: {paper.title}\n"
        f"Authors: {_format_authors(paper.authors)}\n"
        f"Primary category: {paper.primary_category}\n"
        f"Comment: {paper.comment or '—'}\n"
        f"Abstract: {paper.abstract}"
    )


async def classify_paper(paper: Paper) -> ClassificationResult:
    """Classify a single paper as useful vs noise from its metadata.

    The ``rationale`` is generated now but not yet threaded forward; it will be
    persisted alongside the classification result in the storage step (objective.md §6.1).
    """
    return await complete_structured(_SYSTEM_PROMPT, _format_metadata(paper), ClassificationResult)
