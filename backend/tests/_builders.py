"""Shared test factories. Imported normally (not via conftest)."""

from datetime import UTC, datetime

from arxiv_digest.clients.arxiv import Author, Paper

_FIXED_DT = datetime(2024, 1, 1, tzinfo=UTC)


def make_paper(**overrides: object) -> Paper:
    """Build a Paper with neutral defaults; pass only the fields a test cares about."""
    defaults: dict[str, object] = {
        "arxiv_id": "2401.00001",
        "entry_id": "http://arxiv.org/abs/2401.00001",
        "title": "A Paper",
        "abstract": "An abstract.",
        "authors": [Author(name="Ada Lovelace")],
        "primary_category": "cs.LG",
        "categories": ["cs.LG"],
        "published": _FIXED_DT,
        "updated": _FIXED_DT,
        "pdf_url": "http://arxiv.org/pdf/2401.00001",
    }
    return Paper(**(defaults | overrides))  # type: ignore[arg-type]
