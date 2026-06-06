"""The weekly arXiv ingestion workflow.

`DigestWorkflow` is the single, explicit definition of the pipeline: every stage is
a ``@step`` method here, in order. Each step calls into its stage's logic function
under `arxiv_digest.steps`, then returns the event that triggers the next stage.
Orchestration concerns — order, error handling, and branching — live here in one
readable place; the heavy lifting lives in the step modules.

Classification and parsing are interleaved per paper to maximise concurrency: each
paper is classified independently, and a paper marked *useful* starts parsing
immediately (without waiting for the rest to be classified), while *noise* papers
skip the expensive parse entirely. The fan-in happens after parsing.

Event flow:

    StartEvent           ->  ingest              ->  PapersFetchedEvent
    PapersFetchedEvent   ->  classify (fan-out)  ->  ClassifyPaperEvent (per paper)
    ClassifyPaperEvent   ->  classify_one        ->  ParsePaperEvent (useful)
                                                  |  PaperResolvedEvent(None) (noise)
    ParsePaperEvent      ->  parse_one           ->  PaperResolvedEvent (parsed / dropped)
    PaperResolvedEvent   ->  collect_parsed      ->  ParsedEvent (fan-in)
    ParsedEvent          ->  categorize          ->  CategorizedEvent
    CategorizedEvent     ->  summarize           ->  SummarizedEvent
    SummarizedEvent      ->  store               ->  StoredEvent
    StoredEvent          ->  distribute          ->  StopEvent
"""

import logging

from workflows import Context, Workflow, step
from workflows.events import StartEvent, StopEvent

from arxiv_digest.clients.parse import ParseError
from arxiv_digest.config import settings
from arxiv_digest.steps.categorization.events import CategorizedEvent
from arxiv_digest.steps.categorization.step import categorize_papers
from arxiv_digest.steps.classification.events import ClassifyPaperEvent
from arxiv_digest.steps.classification.step import classify_paper
from arxiv_digest.steps.distribution.step import send_digest
from arxiv_digest.steps.ingestion.events import PapersFetchedEvent
from arxiv_digest.steps.ingestion.step import fetch_papers
from arxiv_digest.steps.parsing.events import PaperResolvedEvent, ParsedEvent, ParsePaperEvent
from arxiv_digest.steps.parsing.step import parse_paper
from arxiv_digest.steps.storage.events import StoredEvent
from arxiv_digest.steps.storage.step import store_papers
from arxiv_digest.steps.summarization.events import SummarizedEvent
from arxiv_digest.steps.summarization.step import summarize_papers

logger = logging.getLogger(__name__)

_PAPER_TOTAL = "paper_total"


class DigestWorkflow(Workflow):
    """Ingest -> classify -> parse -> categorize -> summarize -> store -> distribute."""

    @step
    async def ingest(self, ev: StartEvent) -> PapersFetchedEvent:
        """Fetch recent arXiv papers (metadata + PDFs).

        Categories come from settings. The result cap and look-back window also
        default to settings but can be overridden per run via
        ``workflow.run(max_results=5, days_back=7)``.
        """
        max_results = ev.get("max_results", settings.max_results)
        days_back = ev.get("days_back", settings.days_back)
        papers = await fetch_papers(max_results=max_results, days_back=days_back)
        return PapersFetchedEvent(papers=papers)

    @step
    async def classify(
        self, ctx: Context, ev: PapersFetchedEvent
    ) -> ClassifyPaperEvent | ParsedEvent | None:
        """Fan out one classification per paper, bounded by ``llm_max_concurrency``.

        With no papers, no worker ever runs, so emit an empty ``ParsedEvent``
        directly rather than waiting on a fan-in that would never complete.
        """
        if not ev.papers:
            return ParsedEvent(papers=[])
        await ctx.store.set(_PAPER_TOTAL, len(ev.papers))
        for paper in ev.papers:
            ctx.send_event(ClassifyPaperEvent(paper=paper))
        return None

    @step(num_workers=settings.llm_max_concurrency)
    async def classify_one(self, ev: ClassifyPaperEvent) -> ParsePaperEvent | PaperResolvedEvent:
        """Classify a single paper; route useful papers to parsing, drop noise."""
        result = await classify_paper(ev.paper)
        if result.label == "useful":
            return ParsePaperEvent(paper=ev.paper)
        return PaperResolvedEvent(paper=None)

    @step(num_workers=settings.parse_max_concurrency)
    async def parse_one(self, ev: ParsePaperEvent) -> PaperResolvedEvent:
        """Parse a single useful paper; drop it (don't fail the run) if parsing errors."""
        try:
            parsed = await parse_paper(ev.paper)
        except ParseError:
            logger.warning("parse failed for %s; dropping", ev.paper.arxiv_id, exc_info=True)
            return PaperResolvedEvent(paper=None)
        return PaperResolvedEvent(paper=parsed)

    @step
    async def collect_parsed(self, ctx: Context, ev: PaperResolvedEvent) -> ParsedEvent | None:
        """Fan in every per-paper outcome, keeping the useful papers that parsed."""
        total = await ctx.store.get(_PAPER_TOTAL)
        done = ctx.collect_events(ev, [PaperResolvedEvent] * total)
        if done is None:
            return None
        papers = [e.paper for e in done if e.paper is not None]
        return ParsedEvent(papers=papers)

    @step
    async def categorize(self, ev: ParsedEvent) -> CategorizedEvent:
        """Assign one or more topic tags to each paper."""
        papers = await categorize_papers(ev.papers)
        return CategorizedEvent(papers=papers)

    @step
    async def summarize(self, ev: CategorizedEvent) -> SummarizedEvent:
        """Generate short and long summaries for each paper."""
        papers = await summarize_papers(ev.papers)
        return SummarizedEvent(papers=papers)

    @step
    async def store(self, ev: SummarizedEvent) -> StoredEvent:
        """Persist papers, summaries, and embeddings."""
        papers = await store_papers(ev.papers)
        return StoredEvent(papers=papers)

    @step
    async def distribute(self, ev: StoredEvent) -> StopEvent:
        """Render and send the weekly digest, then end the run."""
        await send_digest(ev.papers)
        return StopEvent(result=ev.papers)
