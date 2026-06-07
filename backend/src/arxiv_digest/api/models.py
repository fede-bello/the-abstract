"""API request/response models — the JSON contract the frontend consumes.

These mirror ``frontend/src/data/types.ts`` exactly (snake_case, except the two camelCase
fields the contract fixes: ``weekKey`` and ``paperId``). ``from_attributes`` lets FastAPI
build them straight from the domain objects returned by ``clients/`` (``arxiv.Paper``,
``db.WeekSummary``, ``db.WeekIssue``), dropping internal-only fields like ``pdf_path``.
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from arxiv_digest.clients.arxiv import Author, Summary


class PaperOut(BaseModel):
    """A paper as served to the frontend — ``arxiv.Paper`` minus the internal ``pdf_path``."""

    model_config = ConfigDict(from_attributes=True)

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
    full_text: str | None = None
    topics: list[str]
    summary: Summary | None = None
    classification_rationale: str | None = None


class WeekSummaryOut(BaseModel):
    """A weekly issue's header. ``weekKey`` is camelCase per the frontend contract."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    week_key: str = Field(serialization_alias="weekKey")
    label: str
    count: int
    start: date
    end: date


class WeekIssueOut(BaseModel):
    """A weekly issue: its summary plus that week's papers, newest first."""

    model_config = ConfigDict(from_attributes=True)

    week: WeekSummaryOut
    papers: list[PaperOut]


class TopicCountOut(BaseModel):
    """A topic facet: its display title and how many papers carry it."""

    title: str
    count: int


class AskScope(BaseModel):
    """What a question is scoped to. ``paperId`` is camelCase per the frontend contract."""

    model_config = ConfigDict(populate_by_name=True)

    paper_id: str | None = Field(default=None, alias="paperId")
    topics: list[str] | None = None


class AskRequest(BaseModel):
    """A question for the digest Q&A endpoint."""

    question: str
    scope: AskScope = Field(default_factory=AskScope)


class AskCitation(BaseModel):
    """A paper cited in an answer."""

    arxiv_id: str
    title: str


class AskResponse(BaseModel):
    """An answer plus the papers it draws on."""

    answer: str
    citations: list[AskCitation]
