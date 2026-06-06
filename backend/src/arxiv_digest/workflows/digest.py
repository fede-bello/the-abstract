"""The weekly arXiv ingestion workflow.

`DigestWorkflow` is the single, explicit definition of the pipeline: every stage is
a ``@step`` method here, in order. Each step calls into its stage's logic function
under `arxiv_digest.steps`, then returns the event that triggers the next stage.
Orchestration concerns — order, error handling, and branching — live here in one
readable place; the heavy lifting lives in the step modules.

Per paper, classification fans out first; a *useful* paper is then parsed and
categorized **in parallel** (categorization needs only the abstract, so it doesn't
wait on the slow PDF parse). Summarization is chained onto the parse branch — it reads
the parsed body — and a per-paper join merges that branch with the topics before fan-in.
*Noise* papers skip all of it. The fan-in collects every paper's outcome into one event.
"""

import logging

from workflows import Context, Workflow, step
from workflows.events import StartEvent, StopEvent

from arxiv_digest.clients.parse import ParseError
from arxiv_digest.config import settings
from arxiv_digest.steps.categorization.events import (
    CategorizedEvent,
    CategorizePaperEvent,
    PaperResolvedEvent,
    TopicsAssignedEvent,
)
from arxiv_digest.steps.categorization.step import categorize_paper
from arxiv_digest.steps.classification.events import ClassifyPaperEvent
from arxiv_digest.steps.classification.step import classify_paper
from arxiv_digest.steps.distribution.step import send_digest
from arxiv_digest.steps.ingestion.events import PapersFetchedEvent
from arxiv_digest.steps.ingestion.step import fetch_papers
from arxiv_digest.steps.parsing.events import ParsedPaperEvent, ParsePaperEvent
from arxiv_digest.steps.parsing.step import parse_paper
from arxiv_digest.steps.storage.events import StoredEvent
from arxiv_digest.steps.storage.step import store_papers
from arxiv_digest.steps.summarization.events import SummarizePaperEvent
from arxiv_digest.steps.summarization.step import summarize_paper

logger = logging.getLogger(__name__)

_PAPER_TOTAL = "paper_total"
_JOIN = "join_parts"


class DigestWorkflow(Workflow):
    """Ingest -> classify -> ((parse -> summarize) ∥ categorize) -> store -> distribute."""

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
    ) -> ClassifyPaperEvent | CategorizedEvent | None:
        """Fan out one classification per paper.

        With no papers, no worker ever runs, so emit an empty ``CategorizedEvent``
        directly rather than waiting on a fan-in that would never complete.
        """
        if not ev.papers:
            return CategorizedEvent(papers=[])
        await ctx.store.set(_PAPER_TOTAL, len(ev.papers))
        for paper in ev.papers:
            ctx.send_event(ClassifyPaperEvent(paper=paper))
        return None

    @step(num_workers=settings.llm_max_concurrency)
    async def classify_one(
        self, ctx: Context, ev: ClassifyPaperEvent
    ) -> ParsePaperEvent | CategorizePaperEvent | PaperResolvedEvent | None:
        """Classify a paper; send useful ones to parse and categorize in parallel, drop noise."""
        result = await classify_paper(ev.paper)
        if result.label != "useful":
            return PaperResolvedEvent(paper=None)
        paper = ev.paper.model_copy(update={"classification_rationale": result.rationale})
        ctx.send_event(ParsePaperEvent(paper=paper))
        ctx.send_event(CategorizePaperEvent(paper=paper))
        return None

    @step(num_workers=settings.parse_max_concurrency)
    async def parse_one(self, ev: ParsePaperEvent) -> SummarizePaperEvent | ParsedPaperEvent:
        """Parse a useful paper, then hand it to summarization; drop it if parsing errors."""
        try:
            parsed = await parse_paper(ev.paper)
        except ParseError:
            logger.warning("parse failed for %s; dropping", ev.paper.arxiv_id, exc_info=True)
            return ParsedPaperEvent(arxiv_id=ev.paper.arxiv_id, paper=None)
        return SummarizePaperEvent(paper=parsed)

    @step(num_workers=settings.llm_max_concurrency)
    async def summarize_one(self, ev: SummarizePaperEvent) -> ParsedPaperEvent:
        """Summarize a parsed paper; keep it untouched (no summary) if the LLM errors."""
        paper = ev.paper
        try:
            summary = await summarize_paper(paper)
        except Exception:  # noqa: BLE001 — any backend failure (LLMError/timeout/provider) → no summary
            logger.warning("summarize failed for %s; no summary", paper.arxiv_id, exc_info=True)
            return ParsedPaperEvent(arxiv_id=paper.arxiv_id, paper=paper)
        return ParsedPaperEvent(
            arxiv_id=paper.arxiv_id, paper=paper.model_copy(update={"summary": summary})
        )

    @step(num_workers=settings.llm_max_concurrency)
    async def categorize_one(self, ev: CategorizePaperEvent) -> TopicsAssignedEvent:
        """Tag a useful paper; fall back to no tags (kept, untagged) if the LLM errors."""
        try:
            topics = await categorize_paper(ev.paper)
        except Exception:  # noqa: BLE001 — any backend failure (LLMError/timeout/provider) → untagged
            logger.warning("categorize failed for %s; no tags", ev.paper.arxiv_id, exc_info=True)
            topics = []
        return TopicsAssignedEvent(arxiv_id=ev.paper.arxiv_id, topics=topics)

    @step(num_workers=1)
    async def join_paper(
        self, ctx: Context, ev: ParsedPaperEvent | TopicsAssignedEvent
    ) -> PaperResolvedEvent | None:
        """Merge a paper's parse result and topics once both arrive (serialized, 1 worker)."""
        state = await ctx.store.get(_JOIN, default={})
        entry = state.setdefault(ev.arxiv_id, {})
        if isinstance(ev, ParsedPaperEvent):
            entry["paper"] = ev.paper
        else:
            entry["topics"] = ev.topics
        if "paper" not in entry or "topics" not in entry:
            await ctx.store.set(_JOIN, state)
            return None
        del state[ev.arxiv_id]
        await ctx.store.set(_JOIN, state)
        paper = entry["paper"]
        if paper is None:
            return PaperResolvedEvent(paper=None)
        return PaperResolvedEvent(paper=paper.model_copy(update={"topics": entry["topics"]}))

    @step
    async def collect_resolved(
        self, ctx: Context, ev: PaperResolvedEvent
    ) -> CategorizedEvent | None:
        """Fan in every per-paper outcome, keeping the useful papers that parsed."""
        total = await ctx.store.get(_PAPER_TOTAL)
        done = ctx.collect_events(ev, [PaperResolvedEvent] * total)
        if done is None:
            return None
        papers = [e.paper for e in done if e.paper is not None]
        return CategorizedEvent(papers=papers)

    @step
    async def store(self, ev: CategorizedEvent) -> StoredEvent:
        """Persist papers, summaries, and embeddings."""
        papers = await store_papers(ev.papers)
        return StoredEvent(papers=papers)

    @step
    async def distribute(self, ev: StoredEvent) -> StopEvent:
        """Render and send the weekly digest, then end the run."""
        await send_digest(ev.papers)
        return StopEvent(result=ev.papers)
