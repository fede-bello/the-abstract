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


_DEFAULT_USAGE_WEEKS = 8


async def _run_usage(weeks: int) -> None:
    """Print the weekly LLM + parse usage and estimated cost roll-up, newest first."""
    from arxiv_digest.clients.db import fetch_weekly_usage

    if not settings.supabase_db_url.get_secret_value():
        print("SUPABASE_DB_URL is not set — no usage database to read.")
        return

    rows = await fetch_weekly_usage(weeks)
    if not rows:
        print("No usage recorded yet.")
        return

    header = (
        f"{'week':<12} {'llm':>5} {'in_tok':>9} {'out_tok':>9} "
        f"{'parse':>6} {'pages':>6} {'llm_$':>9} {'parse_$':>9} {'total_$':>9}"
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        week = f"{row.week:%Y-%m-%d}"
        print(
            f"{week:<12} {row.llm_calls:>5} {row.input_tokens:>9} {row.output_tokens:>9} "
            f"{row.parse_jobs:>6} {row.parse_pages:>6} {row.llm_cost_usd:>9.4f} "
            f"{row.parse_cost_usd:>9.4f} {row.total_cost_usd:>9.4f}"
        )


async def _run_preview_email(to: str, count: int) -> None:
    """Send a dummy digest to ``to`` for iterating on the email design."""
    from arxiv_digest.steps.distribution.preview import send_preview

    await send_preview(to, count)
    print(f"Sent a {count}-paper preview digest to {to}.")


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

    usage = subparsers.add_parser("usage", help="Show weekly LLM + parse usage and estimated cost.")
    usage.add_argument(
        "--weeks",
        type=_positive_int,
        default=_DEFAULT_USAGE_WEEKS,
        help=f"How many recent weeks to show (default {_DEFAULT_USAGE_WEEKS}).",
    )

    preview = subparsers.add_parser(
        "preview-email", help="Email a dummy digest to preview the design (no pipeline)."
    )
    preview.add_argument("--to", required=True, help="Recipient address for the preview.")
    preview.add_argument(
        "--count", type=_positive_int, default=20, help="How many dummy papers (default 20)."
    )

    args = parser.parse_args()

    if args.command == "ingest":
        max_results = args.max_results if args.max_results is not None else settings.max_results
        days_back = args.days_back if args.days_back is not None else settings.days_back
        asyncio.run(_run_ingest(max_results, days_back))
    elif args.command == "usage":
        asyncio.run(_run_usage(args.weeks))
    elif args.command == "preview-email":
        asyncio.run(_run_preview_email(args.to, args.count))


if __name__ == "__main__":
    main()
