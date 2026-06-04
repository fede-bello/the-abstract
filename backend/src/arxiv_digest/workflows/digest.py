"""The weekly arXiv ingestion workflow.

`DigestWorkflow` is the single, explicit definition of the pipeline: every stage is
a ``@step`` method here, in order. Each step calls into its stage's logic function
under `arxiv_digest.steps`, then returns the event that triggers the next stage.
Orchestration concerns — order, error handling, and (eventually) branching — live
here in one readable place; the heavy lifting lives in the step modules.

Event flow:

    StartEvent          ->  ingest      ->  PapersFetchedEvent
    PapersFetchedEvent  ->  classify    ->  ClassifiedEvent
    ClassifiedEvent     ->  parse       ->  ParsedEvent
    ParsedEvent         ->  categorize  ->  CategorizedEvent
    CategorizedEvent    ->  summarize   ->  SummarizedEvent
    SummarizedEvent     ->  store       ->  StoredEvent
    StoredEvent         ->  distribute  ->  StopEvent
"""

from workflows import Workflow, step
from workflows.events import StartEvent, StopEvent

from arxiv_digest.config import settings
from arxiv_digest.steps.categorization.events import CategorizedEvent
from arxiv_digest.steps.categorization.step import categorize_papers
from arxiv_digest.steps.classification.events import ClassifiedEvent
from arxiv_digest.steps.classification.step import classify_papers
from arxiv_digest.steps.distribution.step import send_digest
from arxiv_digest.steps.ingestion.events import PapersFetchedEvent
from arxiv_digest.steps.ingestion.step import fetch_papers
from arxiv_digest.steps.parsing.events import ParsedEvent
from arxiv_digest.steps.parsing.step import parse_papers
from arxiv_digest.steps.storage.events import StoredEvent
from arxiv_digest.steps.storage.step import store_papers
from arxiv_digest.steps.summarization.events import SummarizedEvent
from arxiv_digest.steps.summarization.step import summarize_papers


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
    async def classify(self, ev: PapersFetchedEvent) -> ClassifiedEvent:
        """Keep only the papers the classifier marks as useful."""
        papers = await classify_papers(ev.papers)
        return ClassifiedEvent(papers=papers)

    @step
    async def parse(self, ev: ClassifiedEvent) -> ParsedEvent:
        """Parse each useful paper's PDF into text, figures, and tables."""
        papers = await parse_papers(ev.papers)
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
