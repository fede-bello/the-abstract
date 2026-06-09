"""Benchmark test for the paper classifier.

Integration test: it calls a real LLM backend (Claude Code SDK or LiteLLM), so it is
marked `integration` and skips when no backend is available. Run it with:

    uv run pytest -m integration backend/tests/test_classification.py
"""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from arxiv_digest.clients.arxiv import Author, Paper
from arxiv_digest.clients.llm import backend_available
from arxiv_digest.steps.classification.step import classify_paper

_BENCHMARK = Path(__file__).parent / "data" / "classification_benchmark.json"
_FIXED_DT = datetime(2024, 1, 1, tzinfo=UTC)
_MIN_ACCURACY = 0.8


def _to_paper(entry):
    """Build a Paper from a benchmark entry (only metadata fields matter for classify)."""
    return Paper(
        arxiv_id=entry["arxiv_id"],
        entry_id=f"http://arxiv.org/abs/{entry['arxiv_id']}",
        title=entry["title"],
        abstract=entry["abstract"],
        authors=[Author(name=name) for name in entry["authors"]],
        primary_category=entry["primary_category"],
        categories=[entry["primary_category"]],
        comment=entry["comment"],
        published=_FIXED_DT,
        updated=_FIXED_DT,
        pdf_url=f"http://arxiv.org/pdf/{entry['arxiv_id']}",
    )


@pytest.mark.integration
async def test_classifier_benchmark():
    """The classifier should match expected useful/noise labels on the curated set."""
    if not backend_available():
        pytest.skip("no LLM backend available (set LLM_API_KEY or log in to the Claude CLI)")

    entries = json.loads(_BENCHMARK.read_text())
    papers = [_to_paper(e) for e in entries]
    expected = [e["label"] for e in entries]

    results = await asyncio.gather(*(classify_paper(p) for p in papers))
    predicted = [r.label for r in results]

    misses = [
        f"  {e['arxiv_id']} expected={exp} got={pred} :: {e['title'][:55]}"
        for e, exp, pred in zip(entries, expected, predicted, strict=True)
        if exp != pred
    ]
    accuracy = (len(entries) - len(misses)) / len(entries)

    report = f"accuracy {accuracy:.2f} ({len(entries) - len(misses)}/{len(entries)})"
    if misses:
        report += "\nMisclassified:\n" + "\n".join(misses)
    assert accuracy >= _MIN_ACCURACY, report
