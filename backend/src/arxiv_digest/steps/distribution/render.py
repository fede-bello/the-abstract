"""Render the weekly digest as a self-contained HTML email.

Pure functions only, no I/O. Below ``_SPOTLIGHT_MIN`` papers, every paper is shown as a full
card grouped by topic. Past that, the digest splits into a short Spotlight (the standout papers
the insight call picked, as full cards) and a compact "More this week" index (everything else as
one-line links grouped by topic), so a 20+ paper week stays skimmable. All dynamic text is
escaped and styles are inlined, since email clients (Gmail especially) strip <style>, <details>,
and JS. The look mirrors the site: warm paper, one electric-blue accent, monospace labels.
"""

import html
from collections.abc import Collection

from arxiv_digest.clients.arxiv import Paper

_OTHER_SECTION = "Other notable papers"
_MAX_AUTHORS = 4
_ABSTRACT_FALLBACK_CHARS = 320
_TEASER_CHARS = 125
# Below this many papers, show full cards for all; past it, split into Spotlight + compact rest.
_SPOTLIGHT_MIN = 8

# Brand palette + type ("Modern Scientific": warm paper, one electric accent, mono labels).
_PAPER = "#faf9f5"
_CARD = "#ffffff"
_ACCENT = "#0034ff"
_INK = "#16160f"
_BODY = "#403f37"
_MUTED = "#8a897e"
_RULE = "#e9e8e0"
_SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
_MONO = "'SFMono-Regular',ui-monospace,Menlo,Consolas,'Liberation Mono',monospace"


def _format_authors(paper: Paper) -> str:
    """Author names, truncated with 'et al.' past a handful."""
    names = [author.name for author in paper.authors]
    if len(names) > _MAX_AUTHORS:
        return ", ".join(names[:_MAX_AUTHORS]) + ", et al."
    return ", ".join(names)


def _summary_text(paper: Paper) -> str:
    """The paper's short summary as clean prose (falls back to a trimmed abstract).

    ``summary.short`` is prose now, but we defensively collapse any stray bullet markers and
    newlines so older bullet-style summaries still read as a paragraph.
    """
    if not paper.summary:
        return paper.abstract[:_ABSTRACT_FALLBACK_CHARS].strip()
    lines = [line.strip().lstrip("-*•").strip() for line in paper.summary.short.splitlines()]
    return " ".join(line for line in lines if line)


def _teaser(paper: Paper) -> str:
    """A one-line teaser for compact entries: the summary, truncated on a word boundary."""
    text = _summary_text(paper)
    if len(text) <= _TEASER_CHARS:
        return text
    return text[:_TEASER_CHARS].rsplit(" ", 1)[0] + "…"


def _paper_url(paper: Paper, site_url: str | None) -> str:
    """The link a paper's title uses: its page on the site, or the arXiv abstract as fallback."""
    if site_url:
        return f"{site_url.rstrip('/')}/paper/{paper.arxiv_id}"
    return paper.entry_id


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

    Each paper appears once, under its primary (first matching) topic. With ``interests`` set,
    only those topics get sections (and untagged papers are omitted); with no interests, untagged
    papers go to an "Other" section.
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


def _label(text: str, color: str, *, top: int = 0) -> str:
    """A monospace uppercase section label (the brand's signature treatment)."""
    return (
        f'<div style="font-family:{_MONO};font-size:11px;font-weight:700;letter-spacing:1.4px;'
        f'text-transform:uppercase;color:{color};margin:{top}px 0 4px;">{html.escape(text)}</div>'
    )


def _tags_html(paper: Paper) -> str:
    """Topic chips for a full card (mono, subtle)."""
    return "".join(
        f'<span style="display:inline-block;font-family:{_MONO};font-size:10px;font-weight:700;'
        f"letter-spacing:0.4px;background:#eef0ff;color:#2f3bb0;border-radius:3px;"
        f'padding:2px 6px;margin:0 5px 5px 0;">{html.escape(topic)}</span>'
        for topic in paper.topics
    )


def _full_card(paper: Paper, *, first: bool, site_url: str | None) -> str:
    """A full paper card: title (-> site), authors, prose summary, topic chips + arXiv link."""
    divider = "" if first else f"border-top:1px solid {_RULE};"
    title_url = html.escape(_paper_url(paper, site_url))
    return (
        f'<div style="padding:20px 0;{divider}">'
        f'<a href="{title_url}" style="font-family:{_SANS};font-size:17px;'
        f'font-weight:700;line-height:1.32;color:{_INK};text-decoration:none;">'
        f"{html.escape(paper.title)}</a>"
        f'<div style="font-family:{_SANS};font-size:13px;color:{_MUTED};margin:6px 0 11px;">'
        f"{html.escape(_format_authors(paper))}</div>"
        f'<div style="font-family:{_SANS};font-size:14.5px;line-height:1.62;color:{_BODY};'
        f'margin:0 0 13px;">{html.escape(_summary_text(paper))}</div>'
        f"<div>{_tags_html(paper)}"
        f'<a href="{html.escape(paper.entry_id)}" style="font-family:{_MONO};font-size:10px;'
        f"font-weight:700;letter-spacing:0.8px;text-transform:uppercase;color:{_ACCENT};"
        f'text-decoration:none;white-space:nowrap;">Read on arXiv &rsaquo;</a></div>'
        "</div>"
    )


def _compact_row(paper: Paper, *, first: bool, site_url: str | None) -> str:
    """A compact one-line entry: title (-> site) plus a short teaser."""
    divider = "" if first else f"border-top:1px solid {_RULE};"
    title_url = html.escape(_paper_url(paper, site_url))
    return (
        f'<div style="padding:11px 0;{divider}">'
        f'<a href="{title_url}" style="font-family:{_SANS};font-size:14.5px;'
        f'font-weight:600;line-height:1.4;color:{_INK};text-decoration:none;">'
        f"{html.escape(paper.title)}</a>"
        f'<div style="font-family:{_SANS};font-size:13px;line-height:1.5;color:{_MUTED};'
        f'margin-top:3px;">{html.escape(_teaser(paper))}</div>'
        "</div>"
    )


def _full_sections(sections: list[tuple[str, list[Paper]]], site_url: str | None) -> str:
    """Every paper as a full card, grouped under its topic label (small digests)."""
    return "".join(
        _label(title, _ACCENT, top=30)
        + "".join(
            _full_card(paper, first=i == 0, site_url=site_url) for i, paper in enumerate(group)
        )
        for title, group in sections
    )


def _spotlight_and_rest(
    sections: list[tuple[str, list[Paper]]], spotlight: list[Paper], site_url: str | None
) -> str:
    """A Spotlight of full cards, then 'More this week' as compact rows grouped by topic."""
    spot_ids = {paper.arxiv_id for paper in spotlight}
    spot_html = _label("Spotlight", _ACCENT, top=28) + "".join(
        _full_card(paper, first=i == 0, site_url=site_url) for i, paper in enumerate(spotlight)
    )
    rest_groups = []
    for title, group in sections:
        remaining = [paper for paper in group if paper.arxiv_id not in spot_ids]
        if not remaining:
            continue
        rows = "".join(
            _compact_row(paper, first=i == 0, site_url=site_url)
            for i, paper in enumerate(remaining)
        )
        rest_groups.append(_label(title, _MUTED, top=18) + rows)
    rest_html = (
        _label("More this week", _ACCENT, top=34) + "".join(rest_groups) if rest_groups else ""
    )
    return spot_html + rest_html


def render_digest_html(  # noqa: PLR0913 — render entrypoint; keyword-only options, not a god-fn
    heading: str,
    insight: str,
    papers: list[Paper],
    interests: list[str],
    unsubscribe_url: str | None = None,
    *,
    highlights: Collection[str] = (),
    site_url: str | None = None,
) -> str:
    """Build the full HTML email: header, weekly insight, then the papers.

    ``highlights`` are the arXiv ids of the standout papers; past ``_SPOTLIGHT_MIN`` papers they
    become a Spotlight and the rest collapse into a compact index. ``unsubscribe_url`` (when
    given) is rendered as a one-click unsubscribe link in the footer. ``site_url`` (when given)
    makes each paper title link to its page on the site; otherwise titles link to arXiv.
    """
    sections = _group_sections(papers, interests)
    total = sum(len(group) for _, group in sections)
    highlight_order = {arxiv_id: i for i, arxiv_id in enumerate(highlights)}
    spotlight = sorted(
        (
            p
            for p in papers
            if p.arxiv_id in highlight_order and paper_matches_interests(p, interests)
        ),
        key=lambda p: highlight_order[p.arxiv_id],
    )
    body = (
        _spotlight_and_rest(sections, spotlight, site_url)
        if total > _SPOTLIGHT_MIN and spotlight
        else _full_sections(sections, site_url)
    )

    insight_block = (
        f'<div style="border-left:3px solid {_ACCENT};padding:2px 0 2px 16px;margin:20px 0 4px;'
        f'font-family:{_SANS};font-size:15.5px;line-height:1.6;color:{_INK};">'
        f"{html.escape(insight).replace(chr(10), '<br>')}</div>"
        if insight
        else ""
    )
    unsubscribe_block = (
        f' &middot; <a href="{html.escape(unsubscribe_url)}" style="color:{_MUTED};">'
        "Unsubscribe</a>"
        if unsubscribe_url
        else ""
    )
    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="background:{_PAPER};padding:24px 12px;font-family:{_SANS};">'
        '<tr><td align="center">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="max-width:640px;background:{_CARD};border:1px solid {_RULE};border-radius:12px;">'
        f'<tr><td style="height:4px;background:{_ACCENT};'
        'border-radius:12px 12px 0 0;font-size:0;line-height:0;">&nbsp;</td></tr>'
        '<tr><td style="padding:26px 34px 0;">'
        f'<div style="font-family:{_MONO};font-size:11px;font-weight:700;letter-spacing:1.6px;'
        f'text-transform:uppercase;color:{_ACCENT};">arXiv ML Digest</div>'
        f'<h1 style="font-family:{_SANS};font-size:24px;font-weight:800;line-height:1.2;'
        f'color:{_INK};margin:8px 0 0;">{html.escape(heading)}</h1>'
        f"{insight_block}"
        "</td></tr>"
        f'<tr><td style="padding:0 34px 10px;">{body}</td></tr>'
        f'<tr><td style="padding:22px 34px 28px;border-top:1px solid {_RULE};'
        f'font-family:{_MONO};font-size:11px;line-height:1.7;color:{_MUTED};">'
        "You are receiving this because you subscribed to the arXiv ML Digest."
        f"{unsubscribe_block}</td></tr>"
        "</table></td></tr></table>"
    )
