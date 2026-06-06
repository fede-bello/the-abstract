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
    html = render_digest_html("Weekly Digest", "", [_paper("A Paper", ["LLMs"])], [])

    assert "border-left:3px solid" not in html


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


def test_short_summary_renders_as_bullet_list():
    paper = make_paper(
        title="Bulleted",
        topics=["LLMs"],
        summary=Summary(short="- First point.\n- Second point.", long="l", conclusions="c"),
    )

    html = render_digest_html("Digest", "", [paper], [])

    assert "<li" in html
    assert "First point." in html
    assert "Second point." in html
    assert "- First point." not in html


def test_falls_back_to_abstract_when_no_summary():
    paper = make_paper(title="No Summary", topics=["LLMs"], abstract="abstract about transformers")

    html = render_digest_html("Digest", "", [paper], [])

    assert "abstract about transformers" in html
