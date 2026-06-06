"""Summarization logic: generate the short, long, and conclusions summaries for a paper.

The output schema is ``Summary`` (defined alongside ``Paper``): the same model is both
what the LLM returns and what gets stored on the paper. Summaries are written from the
paper's parsed body (``full_text``), so this runs after parsing.
"""

from arxiv_digest.clients.arxiv import Paper, Summary
from arxiv_digest.clients.llm import complete_structured
from arxiv_digest.config import settings

_SYSTEM_PROMPT = (
    "You summarize a machine-learning paper for a weekly research digest. Write three "
    "parts: `short` — 3 to 4 bullet points covering the key contributions and findings, "
    "for quick scanning; `long` — about two paragraphs covering methodology, results, and "
    "implications; `conclusions` — a brief note on the paper's significance and potential "
    "impact. Be specific and faithful to the paper; do not invent results."
)


def _format_input(paper: Paper) -> str:
    """Render the paper for the summarizer: metadata plus the parsed body to summarize."""
    authors = ", ".join(a.name for a in paper.authors) or "—"
    return (
        f"Title: {paper.title}\n"
        f"Authors: {authors}\n"
        f"Abstract: {paper.abstract}\n\n"
        f"Full text:\n{paper.full_text}"
    )


async def summarize_paper(paper: Paper) -> Summary:
    """Generate the short, long, and conclusions summaries for one parsed paper."""
    return await complete_structured(
        _SYSTEM_PROMPT,
        _format_input(paper),
        Summary,
        model=settings.summarization_model,
        max_tokens=settings.summarization_max_output_tokens,
    )
