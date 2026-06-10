"""Unit tests for the digest HTML renderer (pure functions)."""

from _builders import make_paper

from arxiv_digest.clients.arxiv import Paper, Summary
from arxiv_digest.steps.distribution.render import render_digest_html


def _paper(title: str, topics: list[str], **overrides) -> Paper:
    return make_paper(
        title=title,
        topics=topics,
        summary=Summary(short="key result", long="long", conclusions="impact"),
        **overrides,
    )


def test_includes_heading_insight_and_paper_link():
    paper = _paper("Cool Paper", ["LLMs"], entry_id="http://arxiv.org/abs/2401.00001")

    html = render_digest_html("Weekly Digest", "the big insight", [paper], [])

    assert "Weekly Digest" in html
    assert "the big insight" in html
    assert "http://arxiv.org/abs/2401.00001" in html
    assert "Cool Paper" in html
    assert "key result" in html


def test_omits_insight_block_when_insight_is_empty():
    with_insight = render_digest_html("D", "the weekly theme line", [_paper("A", ["LLMs"])], [])
    without = render_digest_html("D", "", [_paper("A", ["LLMs"])], [])

    assert "the weekly theme line" in with_insight
    assert "the weekly theme line" not in without


def test_spotlight_and_compact_index_for_many_papers():
    papers = [_paper(f"Paper {i}", ["LLMs"], arxiv_id=f"id{i}") for i in range(10)]

    html = render_digest_html("Digest", "", papers, [], highlights=["id0", "id1"])

    assert "Spotlight" in html
    assert "More this week" in html
    assert "Paper 0" in html  # spotlighted (full card)
    assert "Paper 9" in html  # compact index


def test_full_cards_below_spotlight_threshold():
    papers = [_paper(f"Paper {i}", ["LLMs"], arxiv_id=f"id{i}") for i in range(3)]

    html = render_digest_html("Digest", "", papers, [], highlights=["id0"])

    assert "Spotlight" not in html
    assert "Paper 2" in html


def test_renders_unsubscribe_link_when_url_given():
    url = "https://x.supabase.co/functions/v1/unsubscribe?token=abc"
    html = render_digest_html("Digest", "", [_paper("A Paper", ["LLMs"])], [], url)

    assert f'href="{url}"' in html
    assert "Unsubscribe" in html


def test_omits_unsubscribe_link_when_no_url():
    html = render_digest_html("Digest", "", [_paper("A Paper", ["LLMs"])], [])

    assert "Unsubscribe" not in html


def test_escapes_html_in_paper_title():
    html = render_digest_html("Digest", "", [_paper("Attention <is> & All", ["LLMs"])], [])

    assert "Attention &lt;is&gt; &amp; All" in html
    assert "<is>" not in html


def test_paper_appears_once_with_all_its_topic_tags():
    paper = _paper("Multi Topic", ["LLMs", "Reasoning"])

    html = render_digest_html("Digest", "", [paper], [])

    assert html.count("Multi Topic") == 1
    assert "LLMs" in html
    assert "Reasoning" in html


def test_untagged_paper_shown_in_other_section_for_all_topics():
    html = render_digest_html("Digest", "", [_paper("Untagged", [])], [])

    assert "Other notable papers" in html
    assert "Untagged" in html


def test_untagged_paper_omitted_when_interests_set():
    papers = [_paper("On LLMs", ["LLMs"]), _paper("Untagged", [])]

    html = render_digest_html("Digest", "", papers, ["LLMs"])

    assert "On LLMs" in html
    assert "Untagged" not in html
    assert "Other notable papers" not in html


def test_short_summary_renders_as_prose_paragraph():
    # `short` is prose now; any stray bullet markers collapse into one clean paragraph.
    paper = make_paper(
        title="Prosey",
        topics=["LLMs"],
        summary=Summary(short="- First point.\n- Second point.", long="l", conclusions="c"),
    )

    html = render_digest_html("Digest", "", [paper], [])

    assert "<li" not in html
    assert "First point. Second point." in html
    assert "- First point." not in html


def test_falls_back_to_abstract_when_no_summary():
    paper = make_paper(title="No Summary", topics=["LLMs"], abstract="abstract about transformers")

    html = render_digest_html("Digest", "", [paper], [])

    assert "abstract about transformers" in html
