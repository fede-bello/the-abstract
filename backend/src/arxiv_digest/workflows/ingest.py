"""The weekly arXiv ingestion pipeline — step wiring and explicit order.

Importing this module registers every stage on `DigestWorkflow` (each step's
``@step`` decorator runs on import) and exposes the ordered pipeline.

Event flow (each step consumes the event on the left and emits the one on the
right; the engine routes on these event types):

    StartEvent          ->  fetch_papers  ->  PapersFetchedEvent
    PapersFetchedEvent  ->  classify      ->  ClassifiedEvent
    ClassifiedEvent     ->  parse         ->  ParsedEvent
    ParsedEvent         ->  categorize    ->  CategorizedEvent
    CategorizedEvent    ->  summarize     ->  SummarizedEvent
    SummarizedEvent     ->  store         ->  StoredEvent
    StoredEvent         ->  distribute    ->  StopEvent
"""

from arxiv_digest.steps.categorization.step import categorize
from arxiv_digest.steps.classification.step import classify
from arxiv_digest.steps.distribution.step import distribute
from arxiv_digest.steps.ingestion.step import fetch_papers
from arxiv_digest.steps.parsing.step import parse
from arxiv_digest.steps.storage.step import store
from arxiv_digest.steps.summarization.step import summarize
from arxiv_digest.workflows.digest import DigestWorkflow

# The pipeline stages in execution order. This tuple is the single explicit
# statement of order; importing the steps above also registers them on the workflow.
PIPELINE = (
    fetch_papers,
    classify,
    parse,
    categorize,
    summarize,
    store,
    distribute,
)

__all__ = ["PIPELINE", "DigestWorkflow"]
