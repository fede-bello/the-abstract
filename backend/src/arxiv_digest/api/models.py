"""Request/response models for the ``/ask`` endpoint — the JSON contract the frontend consumes.

These mirror the Q&A types in ``frontend/src/data/types.ts`` (snake_case, except ``paperId``
which the frontend contract fixes as camelCase). Everything else the SPA reads straight from
Supabase, so no paper/week models live here.
"""

from pydantic import BaseModel, ConfigDict, Field


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
