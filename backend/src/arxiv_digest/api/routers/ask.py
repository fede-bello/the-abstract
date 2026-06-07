"""Q&A endpoint. Placeholder for now — real RAG over the paper chunks lands in a follow-up.

The frontend keeps its PreviewBanner while this returns an honest "coming soon" answer; it
never fabricates papers or citations.
"""

from fastapi import APIRouter

from arxiv_digest.api.models import AskRequest, AskResponse

router = APIRouter(tags=["ask"])

_PLACEHOLDER_ANSWER = (
    "Q&A over the digest isn't available yet — retrieval-augmented answers over the indexed "
    "papers are coming soon. In the meantime, browse the weekly issues and use the filters to "
    "find papers by topic, category, date, or keyword."
)


@router.post("/ask")
async def ask(request: AskRequest) -> AskResponse:  # noqa: ARG001 — body parsed by FastAPI; RAG will use it
    """Return an honest placeholder answer with no citations (real RAG is a follow-up)."""
    return AskResponse(answer=_PLACEHOLDER_ANSWER, citations=[])
