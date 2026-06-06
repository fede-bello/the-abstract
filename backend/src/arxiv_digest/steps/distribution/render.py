"""Render the weekly digest as a self-contained HTML email.

Pure functions only — no I/O. Papers are grouped into sections by their primary (first matching)
topic — each paper appears once, with its other topics still shown as tags; untagged papers fall
into an "Other" section shown only to all-topics subscribers. All dynamic text is escaped and
styles are inlined for email clients.
"""

import html

from arxiv_digest.clients.arxiv import Paper

_OTHER_SECTION = "Other notable papers"
_MAX_AUTHORS = 5
_ABSTRACT_FALLBACK_CHARS = 400


def _format_authors(paper: Paper) -> str:
    """Author names, truncated with 'et al.' past a handful."""
    names = [author.name for author in paper.authors]
    if len(names) > _MAX_AUTHORS:
        return ", ".join(names[:_MAX_AUTHORS]) + ", et al."
    return ", ".join(names)


def _summary_html(paper: Paper) -> str:
    """The paper's short summary as a bullet list, falling back to a trimmed abstract."""
    if not paper.summary:
        abstract = html.escape(paper.abstract[:_ABSTRACT_FALLBACK_CHARS])
        return f'<p style="font-size:13px;color:#222;line-height:1.5;margin:4px 0;">{abstract}</p>'
    bullets = [line.strip().lstrip("-*•").strip() for line in paper.summary.short.splitlines()]
    items = "".join(
        f'<li style="margin:2px 0;">{html.escape(bullet)}</li>' for bullet in bullets if bullet
    )
    return (
        '<ul style="font-size:13px;color:#222;line-height:1.5;margin:4px 0;padding-left:18px;">'
        f"{items}</ul>"
    )


def _matching_topics(paper: Paper, interests: list[str]) -> list[str]:
    """The paper's topics a subscriber cares about — all of them when ``interests`` is empty."""
    if not interests:
        return list(paper.topics)
    interest_set = set(interests)
    return [topic for topic in paper.topics if topic in interest_set]


def paper_matches_interests(paper: Paper, interests: list[str]) -> bool:
    """Whether a paper belongs in this subscriber's digest (any matching topic, or no interests)."""
    return not interests or bool(_matching_topics(paper, interests))


def _group_sections(papers: list[Paper], interests: list[str]) -> list[tuple[str, list[Paper]]]:
    """Group papers into ``(topic, papers)`` sections, ordered by size then name.

    Each paper appears once, under its primary (first matching) topic — its other topics still
    show as tags on the paper itself. With ``interests`` set, only those topics get sections (and
    untagged papers are omitted); with no interests, untagged papers go to an "Other" section.
    """
    by_topic: dict[str, list[Paper]] = {}
    untagged: list[Paper] = []
    for paper in papers:
        topics = _matching_topics(paper, interests)
        if topics:
            by_topic.setdefault(topics[0], []).append(paper)
        elif not interests:
            untagged.append(paper)
    sections = sorted(by_topic.items(), key=lambda item: (-len(item[1]), item[0]))
    if untagged:
        sections.append((_OTHER_SECTION, untagged))
    return sections


def _paper_html(paper: Paper) -> str:
    """One paper block: linked title, authors, topic tags, short summary."""
    tags = " ".join(
        f'<span style="background:#eef;border-radius:4px;padding:1px 6px;'
        f'font-size:12px;color:#334;">{html.escape(topic)}</span>'
        for topic in paper.topics
    )
    authors = html.escape(_format_authors(paper))
    return (
        '<div style="margin:0 0 20px;">'
        f'<a href="{html.escape(paper.entry_id)}" '
        f'style="font-size:14px;font-weight:600;color:#1a0dab;text-decoration:none;">'
        f"{html.escape(paper.title)}</a>"
        f'<div style="font-size:12px;color:#555;margin:2px 0;">{authors}</div>'
        f'<div style="margin:4px 0;">{tags}</div>'
        f'<div style="font-size:14px;color:#222;line-height:1.5;">{_summary_html(paper)}</div>'
        "</div>"
    )


def _section_html(title: str, papers: list[Paper]) -> str:
    """A topic heading followed by its papers."""
    body = "".join(_paper_html(paper) for paper in papers)
    return (
        f'<h2 style="font-size:18px;color:#111;border-bottom:1px solid #ddd;'
        f'padding-bottom:4px;margin:28px 0 16px;">{html.escape(title)}</h2>{body}'
    )


def render_digest_html(
    heading: str, insight: str, papers: list[Paper], interests: list[str]
) -> str:
    """Build the full HTML email: heading, weekly insight, then papers grouped by topic."""
    sections = _group_sections(papers, interests)
    insight_block = (
        f'<p style="font-size:15px;color:#333;line-height:1.6;background:#f7f7f9;'
        f'border-left:3px solid #1a0dab;padding:12px 16px;margin:0 0 24px;">'
        f"{html.escape(insight).replace(chr(10), '<br>')}</p>"
        if insight
        else ""
    )
    body = "".join(_section_html(title, group) for title, group in sections)
    return (
        '<div style="max-width:680px;margin:0 auto;font-family:Helvetica,Arial,sans-serif;">'
        f'<h1 style="font-size:22px;color:#111;">{html.escape(heading)}</h1>'
        f"{insight_block}{body}"
        '<p style="font-size:12px;color:#999;margin-top:32px;">'
        "You are receiving this because you subscribed to the arXiv ML digest.</p>"
        "</div>"
    )
