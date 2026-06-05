"""Command-line entry point for arxiv-digest."""

import argparse
import asyncio
import logging
from typing import TYPE_CHECKING

from arxiv_digest.config import settings
from arxiv_digest.workflows.digest import DigestWorkflow

if TYPE_CHECKING:
    from arxiv_digest.clients.arxiv import Paper


def _positive_int(value: str) -> int:
    """Parse a strictly positive integer for argparse, or raise a clear error."""
    parsed = int(value)
    if parsed <= 0:
        msg = f"expected a positive integer, got {value!r}"
        raise argparse.ArgumentTypeError(msg)
    return parsed


async def _run_ingest(max_results: int, days_back: int) -> None:
    """Run the ingestion pipeline once and print the fetched papers with their dates."""
    # The timeout (default 24h) must outlast a long arXiv backoff; see settings.
    workflow = DigestWorkflow(timeout=settings.workflow_timeout_seconds, verbose=True)
    result = await workflow.run(max_results=max_results, days_back=days_back)
    papers: list[Paper] = result if isinstance(result, list) else []

    print(f"\nPipeline finished — {len(papers)} papers from the last {days_back} days.")
    for paper in papers:
        print(f"  [{paper.published:%Y-%m-%d}] {paper.primary_category:8} {paper.title}")


def main() -> None:
    """Parse arguments and dispatch the requested command."""
    logging.basicConfig(level=settings.log_level, format="%(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(prog="arxiv-digest", description="arXiv ML Digest pipeline.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest", help="Run the weekly ingestion pipeline once.")
    ingest.add_argument(
        "--max-results", type=_positive_int, help="Cap the number of papers fetched."
    )
    ingest.add_argument(
        "--days-back", type=_positive_int, help="Only fetch papers from the last N days."
    )

    args = parser.parse_args()

    if args.command == "ingest":
        max_results = args.max_results if args.max_results is not None else settings.max_results
        days_back = args.days_back if args.days_back is not None else settings.days_back
        asyncio.run(_run_ingest(max_results, days_back))


if __name__ == "__main__":
    main()
